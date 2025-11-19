import requests
from datetime import datetime
import json
import os
import pandas as pd
import re

from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter, Retry

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.3)
session.mount("https://", HTTPAdapter(max_retries=retries))

# Filters
SENIOR_KEYWORDS = [
    r"\bsenior\b", r"\bsr\b", r"\bsr\.\b", r"lead\b", r"principal\b", r"staff\b",
    r"manager\b", r"mgr\b", r"director\b", r"head\b", r"vp\b", r"vice president\b",
    r"chief\b", r"architect\b", r"expert\b", r"specialist\b",
    r"\biii\b", r"\biv\b", r"\bv\b", r"\bvi\b",
    r"\b3\+", r"\b4\+", r"\b5\+", r"\b6\+", r"\b7\+", r"\b8\+",
    r"3-5", r"4-6", r"5-7", r"5\+", r"6\+", r"7\+", r"8\+",
    r"7-10", r"10\+", r"10 years", r"executive\b", r"distinguished\b"
]

JUNIOR_KEYWORDS = [
    r"\bjunior\b", r"\bjr\b", r"\bjr\.\b", r"entry[- ]?level", r"\bassociate\b",
    r"new[- ]?grad", r"early[- ]?career", r"graduate\b", r"grad\b",
    r"\b(i|1)\b", r"level 1\b", r"level i\b",
    r"0-1", r"0-2", r"1-2", r"1-3",
    r"apprentice", r"fellowship", r"rotation", r"trainee",
    r"\bintern\b", r"internship", r"co-op\b", r"coop\b",
    r"campus\b", r"university\b", r"college\b", r"student\b",
    r"recent grad", r"new grad"
]

REMOTE_WORDS = [
    "remote", "anywhere", "distributed", "global",
    "virtually", "telecommute", "worldwide", "work from home",
    "wfh", "location independent", "remote-first", "remote first",
    "fully remote", "100% remote", "flexible location",
    "work anywhere", "remote ok", "remote friendly"
]


ROLE_KEYWORDS = [
    # Software engineering - general
    "software engineer", "swe", "software developer", "developer", "programmer",
    "full stack", "fullstack", "full-stack",
    "frontend", "front end", "front-end", "backend", "back end", "back-end",
    "web developer", "web engineer", "web application",
    "application developer", "application engineer", "app developer",
    "software development", "engineer",

    # Mobile & platforms
    "mobile engineer", "mobile developer",
    "ios engineer", "ios developer", "swift developer",
    "android engineer", "android developer", "kotlin developer",
    "react native", "flutter developer",

    # Infrastructure & DevOps
    "devops", "dev ops", "sre", "site reliability", "reliability engineer",
    "platform engineer", "infrastructure engineer", "systems engineer",
    "cloud engineer", "cloud developer", "aws engineer", "azure engineer", "gcp engineer",
    "kubernetes", "docker", "container", "orchestration",
    "automation engineer", "build engineer", "release engineer",
    "ci/cd", "pipeline engineer",

    # Database & data infrastructure
    "database engineer", "database developer", "dba",
    "sql developer", "nosql", "database administrator",
    "data infrastructure",

    # Security
    "security engineer", "application security", "appsec",
    "security software", "cybersecurity engineer", "infosec",
    "security developer",

    # Testing & QA
    "qa engineer", "quality assurance", "test engineer", "sdet",
    "automation engineer", "test automation", "qa automation",
    "software test", "quality engineer",

    # Embedded & hardware
    "embedded engineer", "embedded software", "firmware engineer",
    "embedded systems", "hardware engineer", "iot engineer",

    # Game development
    "game developer", "game engineer", "game programmer", "gameplay engineer",
    "gameplay programmer", "game designer",
    "unity developer", "unity engineer", "unreal developer", "unreal engineer",
    "graphics engineer", "graphics programmer", "rendering engineer",
    "tools engineer", "tools programmer", "engine programmer",
    "technical artist", "technical designer",
    "3d programmer", "physics programmer", "ai programmer",
    "multiplayer engineer", "network programmer",

    # Data science & ML
    "data scientist", "data science", "research scientist",
    "machine learning engineer", "ml engineer", "mle",
    "machine learning scientist", "applied scientist",
    "ai engineer", "ai developer", "artificial intelligence",
    "deep learning", "computer vision", "nlp engineer",
    "ml ops", "mlops", "ml infrastructure",

    # Data engineering & analytics
    "data engineer", "data engineering",
    "analytics engineer", "data analyst", "business analyst",
    "data pipeline", "data platform", "etl engineer", "etl developer",
    "big data", "data warehouse", "business intelligence", "bi developer",
    "data visualization",

    # Research & specialized
    "research engineer", "research software engineer",
    "computational", "algorithm engineer", "quantitative developer",
    "scientific computing", "hpc engineer",

    # Web3 & blockchain
    "blockchain engineer", "blockchain developer",
    "smart contract", "solidity developer", "web3 developer",
    "crypto engineer", "defi engineer",

    # UI/UX engineering
    "ui engineer", "ux engineer", "design engineer",
    "frontend engineer", "creative technologist"
]

def contains_keywords(text, patterns):
    return any(re.search(pattern, text) for pattern in patterns)

def is_relevant_role(title_lower):
    return any(keyword in title_lower for keyword in ROLE_KEYWORDS)

def load_companies():
    if os.path.exists('companies.json'):
        with open('companies.json', 'r') as f:
            return json.load(f)
    else:
        return {}

# --- Greenhouse ---
def scrape_greenhouse_api(company_name):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_name}/jobs"
    
    try:
        response = session.get(url, timeout=10, params={'content': 'true'})
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []
    
    jobs = []
    
    for job in data.get('jobs', []):
        title = job.get('title', '')
        location = job.get('location', {}).get('name', 'Not specified')
        url_link = job.get('absolute_url', '')
    
        if not url_link or not url_link.startswith("http"):
            continue

        tl = title.lower()
        ll = location.lower() if location else ""
                
        is_senior = contains_keywords(tl, SENIOR_KEYWORDS)
        is_junior_explicit = contains_keywords(tl, JUNIOR_KEYWORDS)
        is_remote = any(word in ll for word in REMOTE_WORDS) or "remote" in tl
    
        posted_date = None
        if 'updated_at' in job:
            try:
                posted_date = datetime.fromisoformat(job['updated_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            except:
                pass

        if not is_senior:
            jobs.append({
                'title': title,
                'company': job.get('company_name', company_name),
                'location': location,
                'url': url_link,
                'source': 'Greenhouse',
                'junior_explicit': is_junior_explicit,
                'is_remote': is_remote,
                'posted_date': posted_date,
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    if jobs:
        print(f"{company_name}: Found {len(jobs)} matching jobs")
    
    return jobs

# --- Lever ---
def scrape_lever_api(company_name):
    url = f"https://api.lever.co/v0/postings/{company_name}"
    
    try:
        response = session.get(url, timeout=10, params={'mode': 'json'})
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []
    
    jobs = []
    
    for job in data:
        title = job.get('text', '')
        location = job.get('categories', {}).get('location', 'Not specified')
        url_link = job.get('hostedUrl', '')
        
        if not url_link or not url_link.startswith("http"):
            continue
        
        tl = title.lower()
        ll = location.lower()
        
        is_senior = contains_keywords(tl, SENIOR_KEYWORDS)
        is_junior_explicit = contains_keywords(tl, JUNIOR_KEYWORDS)
        is_remote = any(word in ll for word in REMOTE_WORDS) or "remote" in tl
        
        posted_date = None
        if 'createdAt' in job:
            try:
                posted_date = datetime.fromtimestamp(job['createdAt'] / 1000).strftime('%Y-%m-%d')
            except:
                pass

        if not is_senior and is_relevant_role(tl):
            jobs.append({
                'title': title,
                'company': job.get('company', {}).get('name', company_name),
                'location': location,
                'url': url_link,
                'source': 'Lever',
                'junior_explicit': is_junior_explicit,
                'is_remote': is_remote,
                'posted_date': posted_date,
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    if jobs:
        print(f"{company_name} (Lever): {len(jobs)} jobs")
    
    return jobs

# --- Workable ---
def scrape_workable_api(company_name):
    url = f"https://apply.workable.com/api/v3/accounts/{company_name}/jobs"
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []
    
    jobs = []
    
    for job in data.get('jobs', []):
        title = job.get('title', '')
        location = job.get('location', {}).get('country', 'Not specified')
        url_link = job.get('url', '')
        
        if not url_link or not url_link.startswith("http"):
            continue
        
        tl = title.lower()
        ll = location.lower()
        
        is_senior = contains_keywords(tl, SENIOR_KEYWORDS)
        is_junior_explicit = contains_keywords(tl, JUNIOR_KEYWORDS)
        is_remote = any(word in ll for word in REMOTE_WORDS) or "remote" in tl
        
        posted_date = None
        if 'published_on' in job:
            try:
                posted_date = datetime.fromisoformat(job['published_on'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            except:
                pass

        if not is_senior and is_relevant_role(tl):
            jobs.append({
                'title': title,
                'company': company_name.capitalize(),
                'location': location,
                'url': url_link,
                'source': 'Workable',
                'junior_explicit': is_junior_explicit,
                'is_remote': is_remote,
                'posted_date': posted_date,
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    if jobs:
        print(f"{company_name} (Workable): {len(jobs)} jobs")
    
    return jobs

def scrape_all_companies():
    companies = load_companies()
    all_jobs = []
    
    # Greenhouse
    greenhouse_list = companies.get('greenhouse', [])
    print(f"\nScraping {len(greenhouse_list)} Greenhouse companies...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(scrape_greenhouse_api, greenhouse_list)
    for job_list in results:
        all_jobs.extend(job_list)

    # Lever
    lever_list = companies.get('lever', [])
    print(f"\nScraping {len(lever_list)} Lever companies...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(scrape_lever_api, lever_list)
    for job_list in results:
        all_jobs.extend(job_list)

    # Workable
    workable_list = companies.get('workable', [])
    print(f"\nScraping {len(lever_list)} Workable companies...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(scrape_workable_api, workable_list)
    for job_list in results:
        all_jobs.extend(job_list)

    return all_jobs

def save_to_csv(jobs, filename=None):
    if not jobs:
        print("\nNo jobs found")
        return None
    
    df = pd.DataFrame(jobs)
    df = df.drop_duplicates(subset=['title', 'company', 'location'])

    if filename is None:
        filename = f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    df.to_csv(filename, index=False)
    print(f"\nSaved {len(jobs)} jobs to {filename}")
    return df

if __name__ == "__main__":
    print("=" * 60)
    print("JOB SCRAPER - Let's find a job")
    print("=" * 60)
    
    jobs = scrape_all_companies()
    
    if jobs:
        df = save_to_csv(jobs)
        print("\nSaved to CSV")
    else:
        print("\nNo matching jobs found")


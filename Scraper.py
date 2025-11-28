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

# ==========================================
# 1. KEYWORDS & FILTERS
# ==========================================

SENIOR_KEYWORDS = [
    r"\bsenior\b", r"\bsr\b", r"\bsr\.\b", r"lead\b", r"principal\b", r"staff\b",
    r"manager\b", r"mgr\b", r"director\b", r"head\b", r"vp\b", r"vice president\b",
    r"chief\b", r"architect\b", r"expert\b", 
    r"\biii\b", r"\biv\b", r"\bv\b", r"\bvi\b",
    r"\b5\+", r"\b6\+", r"\b7\+", r"\b8\+", 
    r"5-7", r"6\+", r"7\+", r"8\+",
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

MID_LEVEL_KEYWORDS = [
    r"\bii\b", r"\b2\b", # Engineer II
    r"mid[- ]?level", r"intermediate",
    r"\b3\+", r"\b4\+", r"3-5", r"2-4", r"2-5",
    r"sde ii", r"swe ii"
]

REMOTE_WORDS = [
    "remote", "anywhere", "distributed", "global",
    "virtually", "telecommute", "worldwide", "work from home",
    "wfh", "location independent", "remote-first", "remote first",
    "fully remote", "100% remote", "flexible location",
    "work anywhere", "remote ok", "remote friendly"
]

ROLE_KEYWORDS = [
    "software engineer", "swe", "software developer", "developer", "programmer",
    "full stack", "fullstack", "frontend", "backend", "web developer", 
    "cloud engineer", "solutions engineer", "application developer", 
    "engineer", "devops", "sre", "data engineer", "mobile engineer",
    "security engineer", "qa engineer", "game developer", "data scientist"
]

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def contains_keywords(text, patterns):
    return any(re.search(pattern, text) for pattern in patterns)

def is_relevant_role(title_lower):
    return any(keyword in title_lower for keyword in ROLE_KEYWORDS)

def determine_level(title_lower):
    if contains_keywords(title_lower, SENIOR_KEYWORDS):
        return "Senior"
    elif contains_keywords(title_lower, JUNIOR_KEYWORDS):
        return "Junior"
    elif contains_keywords(title_lower, MID_LEVEL_KEYWORDS):
        return "Mid-Level"
    else:
        return "Standard (Mid)"

def load_companies():
    if os.path.exists('companies.json'):
        with open('companies.json', 'r') as f:
            return json.load(f)
    else:
        return {}

def load_hidden_jobs():
    """Loads the list of URLs the user has hidden via the dashboard."""
    if os.path.exists('hidden_jobs.json'):
        try:
            with open('hidden_jobs.json', 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def process_job(title, location, url, company, source, date_posted=None):
    tl = title.lower()
    ll = location.lower() if location else ""
    
    level = determine_level(tl)
    is_remote = any(word in ll for word in REMOTE_WORDS) or "remote" in tl

    return {
        'title': title,
        'company': company,
        'location': location,
        'url': url,
        'source': source,
        'level': level,
        'is_remote': is_remote,
        'posted_date': date_posted,
        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# ==========================================
# 3. API SCRAPERS
# ==========================================

def scrape_greenhouse_api(company_name):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_name}/jobs"
    try:
        response = session.get(url, timeout=10, params={'content': 'true'})
        if response.status_code != 200: return []
        data = response.json()
    except: return []
    
    jobs = []
    for job in data.get('jobs', []):
        title = job.get('title', '')
        if not is_relevant_role(title.lower()): continue
        
        posted_date = None
        if 'updated_at' in job:
            posted_date = job['updated_at'].split('T')[0]

        jobs.append(process_job(
            title, job.get('location', {}).get('name', ''), 
            job.get('absolute_url', ''), job.get('company_name', company_name), 
            'Greenhouse', posted_date
        ))
    return jobs

def scrape_lever_api(company_name):
    url = f"https://api.lever.co/v0/postings/{company_name}"
    try:
        response = session.get(url, timeout=10, params={'mode': 'json'})
        if response.status_code != 200: return []
        data = response.json()
    except: return []
    
    jobs = []
    for job in data:
        title = job.get('text', '')
        if not is_relevant_role(title.lower()): continue
        
        posted_date = None
        if 'createdAt' in job:
            posted_date = datetime.fromtimestamp(job['createdAt'] / 1000).strftime('%Y-%m-%d')

        jobs.append(process_job(
            title, job.get('categories', {}).get('location', ''), 
            job.get('hostedUrl', ''), job.get('company', {}).get('name', company_name), 
            'Lever', posted_date
        ))
    return jobs

def scrape_workable_api(company_name):
    url = f"https://apply.workable.com/api/v3/accounts/{company_name}/jobs"
    try:
        response = session.get(url, timeout=10)
        if response.status_code != 200: return []
        data = response.json()
    except: return []
    
    jobs = []
    for job in data.get('jobs', []):
        title = job.get('title', '')
        if not is_relevant_role(title.lower()): continue
        
        posted_date = None
        if 'published_on' in job:
            posted_date = job['published_on'].split('T')[0]

        jobs.append(process_job(
            title, job.get('location', {}).get('country', ''), 
            job.get('url', ''), company_name.capitalize(), 
            'Workable', posted_date
        ))
    return jobs

def scrape_all_companies():
    companies = load_companies()
    all_jobs = []
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        for system, func in [('Greenhouse', scrape_greenhouse_api), 
                             ('Lever', scrape_lever_api), 
                             ('Workable', scrape_workable_api)]:
            if system in companies:
                print(f"Scraping {system}...")
                results = executor.map(func, companies[system])
                for res in results: all_jobs.extend(res)

    return all_jobs

def save_to_csv(jobs):
    if not jobs: 
        print("No jobs found.")
        return None
    
    # --- FILTER HIDDEN JOBS ---
    hidden_urls = load_hidden_jobs()
    if hidden_urls:
        print(f"Filtering out {len(hidden_urls)} hidden jobs...")
        jobs = [j for j in jobs if j['url'] not in hidden_urls]
    
    if not jobs:
        print("All jobs were hidden or none found.")
        return None
    # --------------------------

    df = pd.DataFrame(jobs)
    df = df.drop_duplicates(subset=['title', 'company', 'location'])
    filename = f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} jobs to {filename}")
    return df

if __name__ == "__main__":
    print("=" * 60)
    print("JOB SCRAPER - Let's find a job")
    print("=" * 60)
    
    jobs = scrape_all_companies()
    if jobs:
        save_to_csv(jobs)
    else:
        print("\nNo matching jobs found")
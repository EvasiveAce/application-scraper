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

def load_companies():
    if os.path.exists('companies.json'):
        with open('companies.json', 'r') as f:
            return json.load(f)
    else:
        return {"greenhouse": ["stripe", "shopify", "gitlab", "figma", "notion"]}

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
        ll = location.lower()
    
        # Filters
        SENIOR_KEYWORDS = [
            r"\bsenior\b", r"\bsr\b", r"lead\b", r"principal\b", r"staff\b",
            r"manager\b", r"director\b", r"head\b", r"vp\b", r"chief\b",
            r"architect\b", r"\biii\b", r"\biv\b", r"\bv\b",
            r"\b5[\+ ]", r"\b6[\+ ]", r"\b7[\+ ]", r"7-10", r"10\+"
        ]

        JUNIOR_KEYWORDS = [
            r"\bjunior\b", r"\bjr\b", r"entry[- ]?level", r"\bassociate\b",
            r"new[- ]?grad", r"early[- ]?career", r"graduate",
            r"\b(i|1)\b", r"0-1", r"0-2", r"1-2",
            r"apprentice", r"fellowship", r"rotation",
        ]
        
        def contains_keywords(text, patterns):
            return any(re.search(pattern, text) for pattern in patterns)

        is_senior = contains_keywords(tl, SENIOR_KEYWORDS)
        is_junior_explicit = contains_keywords(tl, JUNIOR_KEYWORDS)

        REMOTE_WORDS = [
            "remote", "anywhere", "distributed", "global",
            "virtually", "telecommute", "worldwide", "work from home"
        ]

        is_remote = (
            any(word in ll for word in REMOTE_WORDS) or
            "remote" in tl
        )

        ROLE_KEYWORDS = [
            # Software engineering
            "software engineer", "swe", "developer", "programmer",
            "full stack", "frontend", "front end", "backend", "back end",
            "web engineer", "mobile engineer", "ios engineer", "android engineer",
            "platform engineer", "application engineer",
            "systems engineer", "qa engineer", "test engineer", "engineer", 

            # Game development
            "game developer", "game engineer", "gameplay engineer",
            "unity", "unreal", "graphics engineer", "rendering engineer",
            "tools engineer",

            # Data engineering / data roles
            "data engineer", "data engineering", "etl",
            "analytics engineer", "data pipeline", "data platform",
            "machine learning engineer", "ml engineer", "ml ops",
            "ai engineer", "ai developer"
        ]

        def is_relevant_role(title_lower):
            return any(keyword in title_lower for keyword in ROLE_KEYWORDS)
        
        if not is_senior and is_relevant_role(tl):
            jobs.append({
                'title': title,
                'company': job.get('company_name', company_name),
                'location': location,
                'url': url_link,
                'source': 'Greenhouse',
                'junior_explicit': is_junior_explicit,
                'is_remote': is_remote,
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    if jobs:
        print(f"{company_name}: Found {len(jobs)} matching jobs")
    
    return jobs

def scrape_all_companies():
    companies = load_companies()
    all_jobs = []
    
    greenhouse_list = companies.get('greenhouse', [])
    print(f"\nScraping {len(greenhouse_list)} companies...")
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(scrape_greenhouse_api, greenhouse_list)

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


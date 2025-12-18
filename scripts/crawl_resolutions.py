
import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# URL for general legal documents (likely contains Resolutions, Decrees, etc.)
BASE_URL = "https://hethongphapluat.com/van-ban-phap-luat_page-{}.html"
OUTPUT_DIR = r"e:\VSCODE_WORKSPACE\VNPT\data_raw\legal_crawl"
YEARS_TO_CRAWL = [2023, 2024, 2025] # Focus on recent gaps

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_law_content(url):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        content_div = None
        
        selectors = [
            'div.content-detail', 'div#content_detail', 
            'div.news-content', 'div.entry-content', 
            'div#divContent', 'div.vb_content'
        ]
        
        for sel in selectors:
            try:
                tag, cls = sel.split('.')
                found = soup.find(tag, class_=cls)
            except ValueError:
                tag, ident = sel.split('#')
                found = soup.find(tag, id=ident)
            
            if found:
                content_div = found
                break
        
        if not content_div and soup.body:
             # Heuristic for Resolutions: look for "Điều 1." or "QUYẾT NGHỊ"
            match = soup.body.find(string=re.compile(r"(Điều 1\.|QUYẾT NGHỊ|Q U Y Ế T N G H Ị)"))
            if match:
                content_div = match.find_parent('div')
        
        if not content_div:
            h1 = soup.find('h1')
            if h1:
                content_div = h1.find_parent('div')

        if content_div:
            for script in content_div(["script", "style"]):
                script.extract()
            return clean_text(content_div.get_text())
        else:
            return None

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def process_page(page):
    url = BASE_URL.format(page)
    print(f"Crawling page {page}...")
    
    new_docs = []
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.content, 'html.parser')
        links = soup.find_all('a')
        
        processed_urls = set()

        for link in links:
            href = link.get('href', '')
            title = link.get_text().strip()
            
            if not href or not href.endswith('.html') or len(title) < 10:
                continue
            
            if href in processed_urls: continue
            
            # KEYWORD FILTERING
            normalized_title = title.lower()
            
            # Keywords: "sắp xếp" AND "đơn vị hành chính" OR "nghị quyết"
            # We want broad coverage of admin changes.
            is_relevant = False
            if "sắp xếp" in normalized_title and "đơn vị hành chính" in normalized_title:
                is_relevant = True
            elif "nghị quyết" in normalized_title and "ủy ban thường vụ quốc hội" in normalized_title:
                is_relevant = True
            elif "gia lai" in normalized_title: # User specific request
                is_relevant = True

            if not is_relevant:
                continue

            # YEAR FILTERING
            # Try to find year in title
            match = re.search(r'(\d{4})', title)
            year = 0
            if match:
                year = int(match.group(1))
            
            if year in YEARS_TO_CRAWL:
                full_url = href if href.startswith('http') else "https://hethongphapluat.com" + href
                if not href.startswith('http') and href.startswith('/'):
                     full_url = "https://hethongphapluat.com" + href

                if full_url in processed_urls: continue
                processed_urls.add(full_url)
                
                print(f"  Found relevant doc: {title} ({year})")
                
                content = get_law_content(full_url)
                if content:
                    # Sanitize filename
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:50]
                    filename = f"res_{year}_{safe_title}.json"
                    filepath = os.path.join(OUTPUT_DIR, filename)

                    if not os.path.exists(filepath):
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump({
                                "title": title,
                                "url": full_url,
                                "year": year,
                                "content": content
                            }, f, ensure_ascii=False, indent=2)
                        new_docs.append(filename)
    except Exception as e:
        print(f"Error on page {page}: {e}")
        
    return new_docs

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # We'll scan first 50 pages. Since it's sorted by new, 50 pages should cover 2023-2025 easily.
    # Parallel processing for speed? Maybe slow down to avoid ban.
    # Sequential is safer for the site, but we can do parallel pages with delay.
    # Let's do a simple loop.
    
    total_found = 0
    for page in range(1, 51):
        found = process_page(page)
        total_found += len(found)
        if len(found) > 0:
            print(f"  Saved {len(found)} docs from page {page}")
        time.sleep(1)

    print(f"Crawler finished. Total new documents: {total_found}")

if __name__ == "__main__":
    main()

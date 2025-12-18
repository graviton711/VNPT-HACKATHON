
import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "https://vbpl.vn/TW/Pages/vanban.aspx?idLoaiVanBan=22&dvid=13&Page={}"
DOMAIN = "https://vbpl.vn"
DATA_DIR = "data"
TEMP_DIR = os.path.join(DATA_DIR, "temp_thong_tu")
MAX_WORKERS = 40 # High concurrency for pages
TOTAL_PAGES_ESTIMATE = 1800 # 16k items / 10 per page = 1600. Safety margin.

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def get_detail_content(url):
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            return ""
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Try finding content
        content_div = soup.find("div", id="toanvancontent")
        if not content_div:
            content_div = soup.find("div", class_="content-detail")
        
        if content_div:
            for tag in content_div(["script", "style", "iframe"]):
                tag.decompose()
            return content_div.get_text(separator="\n", strip=True)
            
        return ""
    except Exception:
        return ""

def process_page(page):
    output_file = os.path.join(TEMP_DIR, f"page_{page}.json")
    if os.path.exists(output_file):
        # Verify it's valid JSON?
        try:
             with open(output_file, 'r', encoding='utf-8') as f:
                 if json.load(f): return f"Page {page} exists. Skipped."
        except:
            pass # Re-crawl if corrupted

    url = BASE_URL.format(page)
    
    try:
        # Request list page
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return f"Page {page} HTTP {resp.status_code}"
            
        soup = BeautifulSoup(resp.content, 'html.parser')
        list_ul = soup.find("ul", class_="listLaw")
        
        if not list_ul:
            return f"Page {page} no listLaw found."

        items = list_ul.find_all("li")
        if not items:
            return f"Page {page} has 0 items."

        page_data = []
        for li in items:
            div_item = li.find("div", class_="item")
            if not div_item: continue
            
            title_p = div_item.find("p", class_="title")
            if not title_p: continue
            
            a_tag = title_p.find("a")
            if not a_tag: continue
            
            link = a_tag.get('href')
            title = a_tag.get_text(strip=True)
            full_link = DOMAIN + link if link.startswith('/') else link
            
            meta_p = div_item.find("p", class_="green")
            meta_text = meta_p.get_text(strip=True) if meta_p else ""
            
            # Fetch detail immediately (Blocking within this thread)
            # Since we have 40 threads, blocking here is fine, it just means this thread is busy.
            content = get_detail_content(full_link)
            
            doc = {
                "title": title,
                "url": full_link,
                "metadata": meta_text,
                "content": content,
                "type": "Thông tư",
                "source": "vbpl.vn",
                "crawled_at": datetime.now().isoformat(),
                "page": page
            }
            page_data.append(doc)
            
        # Save page immediately
        if page_data:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)
            return f"Page {page} DONE ({len(page_data)} docs)."
        else:
            return f"Page {page} layout match but 0 docs extracted."
            
    except Exception as e:
        return f"Page {page} Error: {e}"

def crawl():
    print(f"Starting parallel crawl (Pages) with {MAX_WORKERS} workers...")
    
    # 1. Determine work
    existing_files = set(os.listdir(TEMP_DIR))
    pages_to_crawl = []
    for p in range(1, TOTAL_PAGES_ESTIMATE + 1):
        if f"page_{p}.json" not in existing_files:
            pages_to_crawl.append(p)
    
    print(f"Found {len(pages_to_crawl)} pages remaining to crawl.")
    
    # 2. Execute
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_page = {executor.submit(process_page, p): p for p in pages_to_crawl}
        
        count = 0
        for future in as_completed(future_to_page):
            count += 1
            res = future.result()
            # print progress every 10 completions
            if count % 10 == 0:
                print(f"Progress: {count}/{len(pages_to_crawl)} completed.")
            
            # Print non-skip messages or errors
            if "DONE" in res or "Error" in res or "HTTP" in res:
                 pass # Silence "DONE" if too noisy? User wants to see speed.
                 print(res)

    print("Crawl session finished. Data is in data/temp_thong_tu/.")

if __name__ == "__main__":
    crawl()

import os
import json
import time
import random
import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup

OUTPUT_DIR = r"e:\VSCODE_WORKSPACE\VNPT\data_raw\luatvietnam_merger"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# User provided URL structure
BASE_SEARCH_URL = "https://luatvietnam.vn/van-ban/tim-van-ban.html?keywords=v%E1%BB%81%20vi%E1%BB%87c%20s%E1%BA%AFp%20x%E1%BA%BFp%20c%C3%A1c%20%C4%91%C6%A1n%20v%E1%BB%8B%20h%C3%A0nh%20ch%C3%ADnh%20c%E1%BA%A5p%20x%C3%A3%20c%E1%BB%A7a&SearchOptions=1&SearchByDate=issueDate&DateFromString=&DateToString=&DocTypeIds=13&OrganIds=0&FieldIds=0&LanguageId=1&SignerIds=0&RowAmount=20"

MAX_CONCURRENCY = 8 # User requested 8 threads/workers

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
    "Connection": "keep-alive"
}

def extract_doc_id(url):
    match = re.search(r'-(\d+)-d\d+\.html', url)
    if match:
        return match.group(1)
    parts = url.split('-')
    if len(parts) > 1:
        possible_id = parts[-1].replace('.html', '').replace('d', '')
        if possible_id.isdigit():
            return possible_id
    return "unknown_" + str(int(time.time()))

async def fetch(session, url, retries=3):
    for i in range(retries):
        try:
            async with session.get(url, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:
                    print(f"    Rate limited (429). Sleeping 10s...")
                    await asyncio.sleep(10)
                else:
                    # print(f"    Status {response.status} for {url}")
                    pass
        except Exception as e:
            # print(f"    Error fetching {url}: {e}")
            await asyncio.sleep(1)
    return None

async def process_document(sem, session, url):
    async with sem:
        doc_id = extract_doc_id(url)
        filename = f"luatvietnam_{doc_id}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)

        if os.path.exists(filepath):
            return

        print(f"  Processing {doc_id}...")
        html = await fetch(session, url)
        if not html:
            print(f"    Failed to fetch {url}")
            return

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Title
            title_el = soup.select_one("h1.the-document-title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                title_el = soup.select_one("h1")
                title = title_el.get_text(strip=True) if title_el else "Unknown Title"

            # Metadata
            metadata = {}
            for row in soup.select("table.table-bordered tr"):
                cols = row.select("td")
                if len(cols) >= 2:
                    k = cols[0].get_text(strip=True).replace(':', '')
                    v = cols[1].get_text(strip=True)
                    metadata[k] = v
                    if len(cols) >= 4:
                        k2 = cols[2].get_text(strip=True).replace(':', '')
                        v2 = cols[3].get_text(strip=True)
                        metadata[k2] = v2
            
            # Content
            content_text = ""
            content_div = soup.select_one("#noidung")
            if content_div:
                # Remove scripts types
                for s in content_div(['script', 'style']):
                    s.decompose()
                content_text = content_div.get_text(separator="\n", strip=True)
            
            if not content_text:
                c2 = soup.select_one(".content-doc")
                if c2:
                     for s in c2(['script', 'style']):
                        s.decompose()
                     content_text = c2.get_text(separator="\n", strip=True)

            if len(content_text) > 50:
                data = {
                    "doc_id": doc_id,
                    "url": url,
                    "title": title,
                    "metadata": metadata,
                    "content": content_text,
                    "crawled_at": time.time()
                }
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"    Saved {doc_id} ({len(content_text)} chars)")
            else:
                print(f"    Skipping {doc_id} - Content empty/short")

        except Exception as e:
            print(f"    Error parsing {doc_id}: {e}")

async def crawl_list_page(session, page_num):
    url = f"{BASE_SEARCH_URL}&PageIndex={page_num}"
    print(f"Crawling List Page {page_num}...")
    
    html = await fetch(session, url)
    if not html:
        return []
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # Check for no results
    if "Không tìm thấy văn bản" in soup.get_text() or "no-result" in str(soup):
         return []

    links = []
    # Selector based on previous debug
    for a in soup.select("div.post-doc h2.doc-title a"):
        href = a.get('href')
        if href:
            if href.startswith("/"):
                links.append("https://luatvietnam.vn" + href)
            elif "luatvietnam.vn" in href:
                links.append(href)
                
    # Deduplicate
    return list(set([l.split("#")[0] for l in links]))

async def run():
    print("Starting Aiohttp Crawler...")
    processed_count = 0
    current_page = 1
    
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    
    async with aiohttp.ClientSession() as session:
        while True:
            urls = await crawl_list_page(session, current_page)
            
            if not urls:
                print(f"No documents found on Page {current_page}. Stopping.")
                break
                
            print(f"Page {current_page}: Found {len(urls)} documents.")
            
            tasks = []
            for url in urls:
                tasks.append(process_document(sem, session, url))
            
            await asyncio.gather(*tasks)
            
            processed_count += len(urls)
            current_page += 1
            
            if current_page > 200:
                print("Limit reached.")
                break
                
            # Random delay
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
    print(f"Finished. Total processed: {processed_count}")

if __name__ == "__main__":
    asyncio.run(run())


import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time

BASE_URL = "https://hethongphapluat.com/van-ban-moi_page-{}.html"
OUTPUT_DIR = r"e:\VSCODE_WORKSPACE\VNPT\data_raw\vbpl"
YEARS_TO_CRAWL = [2024, 2025]

def get_law_metadata(soup):
    meta = {}
    info_div = soup.find('div', id='right-doc-info')
    if info_div:
        uli = info_div.find('ul')
        if uli:
            for li in uli.find_all('li'):
                text = li.get_text(separator=' ', strip=True)
                if ':' in text:
                    key, val = text.split(':', 1)
                    meta[key.strip()] = val.strip()
    return meta

def clean_text(text):
    if not text:
        return ""
    # Remove multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_law_content(url):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"Failed to fetch {url}")
            return None, None
        
        # Determine encoding or force utf-8
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        metadata = get_law_metadata(soup)
        
        content_div = None
        
        # 1. Try explicit classes/IDs found in common VBBPL sites
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
        
        # 2. Heuristic: Look for "Điều 1." which is standard in VN laws
        if not content_div:
            # Find a text node containing "Điều 1."
            # Limit scope to body to avoid errors
            if soup.body:
                match = soup.body.find(string=re.compile(r"Điều 1\."))
                if match:
                    # Traverse up to a block element
                    content_div = match.find_parent('div')
        
        # 3. Fallback: H1's parent
        if not content_div:
            h1 = soup.find('h1')
            if h1:
                content_div = h1.find_parent('div')

        if content_div:
            # Clean scripts and styles from the div
            for script in content_div(["script", "style"]):
                script.extract()
            return clean_text(content_div.get_text()), metadata
        else:
            print(f"Could not find content div for {url}")
            return None, None
            
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None, None

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    page = 1
    total_crawled = 0
    
    while True:
        url = BASE_URL.format(page)
        print(f"Crawling list page: {url}")
        
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                print("Failed to fetch list page. Stopping.")
                break
                
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Find the list of laws. Inspecting usually 'ul' class 'news-list' or similar
            # Based on view_content_chunk, it seems to be standard links.
            # Let's look for 'div' class 'news-item' or 'h3' tags with links inside
            # General approach: Find all 'a' tags, check if title contains relevant year.
            
            # Refined Selector based on typical VN news sites (often news-list > item)
            # But simpler: Find all links with class 'title' or inside h3
            links = soup.find_all('a')
            
            found_on_page = 0
            stop_signal = False # If we see laws way too old?
            
            processed_urls = set()

            for link in links:
                href = link.get('href', '')
                title = link.get_text().strip()
                
                if not href or not href.endswith('.html') or len(title) < 10:
                    continue
                
                if href in processed_urls: continue
                # Relaxed filter for "Van ban moi"
                valid = ["Luật", "Bộ luật", "Nghị định", "Thông tư", "Quyết định", "Chỉ thị", "Nghị quyết"]
                if not any(k in title for k in valid):
                    continue

                # Check Year
                match = re.search(r'(\d{4})', title)
                if match:
                    year = int(match.group(1))
                    
                    if year in YEARS_TO_CRAWL:
                        # Good to crawl
                        full_url = href if href.startswith('http') else "https://hethongphapluat.com" + href  # Usually href is relative or absolute? Check...
                        if not href.startswith('http'):
                             if href.startswith('/'):
                                 full_url = "https://hethongphapluat.com" + href
                             else:
                                 # Some sites are erratic
                                 full_url = "https://hethongphapluat.com/" + href

                        if full_url in processed_urls: continue # Double check
                        processed_urls.add(full_url)

                        print(f"  Found relevant law: {title} ({year})")
                        
                        # Fetch Content
                        content, metadata = get_law_content(full_url)
                        if content:
                            filename = f"vbpl_{year}_{len(os.listdir(OUTPUT_DIR))}.json"
                            
                            with open(os.path.join(OUTPUT_DIR, filename), 'w', encoding='utf-8') as f:
                                json.dump({
                                    "title": title,
                                    "url": full_url,
                                    "year": year,
                                    "metadata": metadata,
                                    "content": content
                                }, f, ensure_ascii=False, indent=2)
                            
                            found_on_page += 1
                            total_crawled += 1
                            time.sleep(1) # Be polite
                    
                    elif year < 2020:
                        # Found an old law. 
                        # Assuming the list is chronological, if we hit < 2020 we might be done.
                        # BUT, pages might be mixed. Let's be cautious.
                        # If a page has mostly old laws, maybe stop? 
                        # Let's just skip this item.
                        pass
            
            if found_on_page == 0 and page > 1:
                # Heuristic: If we parsed a whole page and found nothing relevant, 
                # and verify we actually parsed links (len(links) > something), we might be done.
                # However, maybe page 2 is 2019?
                # Let's rely on the user saying "just 5 years".
                # If we see a sequence of years 2018, 2017... we stop.
                # Since I don't track the *trend*, I'll just check if found_on_page is 0.
                print("No relevant laws found on this page. Stopping.")
                break

            page += 1
            time.sleep(2)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            break

    print(f"Crawler finished. Total documents: {total_crawled}")

if __name__ == "__main__":
    main()

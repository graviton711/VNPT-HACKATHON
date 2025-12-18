import requests
from bs4 import BeautifulSoup
import json
import os
import time

# IDs extracted from the user's HTML source
IDS = [
    "23f45379", # Bài mở đầu
    "2775b6ea", # Ch 1.I
    "79de9c2a", # Ch 1.II
    "917541f9", # Ch 1.III
    "689b0dc2", # Ch 2.I
    "61c681c2", # Ch 2.II
    "93065d1c", # Ch 2.III
    "19472bbf", # Ch 2.IV
    "b4c02a64", # Ch 3.I
    "2b9e5757", # Ch 3.II
    "d71bc267", # Ch 3.III
    "451ce80c", # Ch 3.IV
    "8df94ffb", # Ch 4.I
    "7e31ec3a", # Ch 4.II
    "5bb47cdd", # Ch 4.III
    "87fa9620", # Ch 4.IV
    "c0f2a7e8", # Ch 5.I
    "6c338aac", # Ch 5.II
    "d16be44a", # Ch 6.I
    "c884774d"  # Ch 6.II
]

BASE_URL = "https://voer.edu.vn/m/_/{}"
OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\history_party_voer.json"

def crawl():
    results = []
    print(f"Starting crawl for {len(IDS)} documents...")
    
    for i, doc_id in enumerate(IDS):
        url = BASE_URL.format(doc_id)
        try:
            print(f"[{i+1}/{len(IDS)}] Fetching {url}...")
            # Use a realistic user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Title often in doc_banner_content h1 or similar. 
                # Based on the user's checking of "Tình hình thế giới...", let's look for common title tags.
                title = "Unknown Title"
                h1 = soup.find('h1', class_='title-document') # From user HTML sample: <p class="title-document ..."> (might be p or h1 depending on view)
                if not h1:
                     h1 = soup.select_one('.doc_banner_content h1')
                if not h1:
                    h1 = soup.find('h1')
                
                if h1:
                    title = h1.get_text(strip=True)
                
                # Content
                # The user's HTML showed <div class="forum-post-content ..."> -> <div class="content"> -> <div class="inner-content">
                content_div = soup.select_one('.inner-content')
                if not content_div:
                    content_div = soup.select_one('.forum-post-content')
                
                if content_div:
                    # Remove scripts and styles
                    for script in content_div(["script", "style"]):
                        script.decompose()
                    
                    text_content = content_div.get_text(separator="\n", strip=True)
                else:
                    text_content = ""
                    print("  Warning: No content found.")

                if text_content:
                    results.append({
                        "id": doc_id,
                        "url": url,
                        "title": title,
                        "content_text": text_content,
                        "original_source": "VOER",
                        "license": "CC BY 3.0"
                    })
                    print(f"  Success. Length: {len(text_content)} chars.")
            else:
                print(f"  Failed. Status: {resp.status_code}")
        
        except Exception as e:
            print(f"  Error: {e}")
            
        # Be polite
        time.sleep(1)

    print(f"crawl finished. Saving {len(results)} items to {OUTPUT_FILE}")
    
    # Ensure dir exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    crawl()

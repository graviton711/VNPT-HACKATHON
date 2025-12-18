import requests
from bs4 import BeautifulSoup
import json
import os
import time

# IDs extracted from the user's provided URL
IDS = [
    "0a6b4ca8", # Lời mở đầu - Kinh tế vi mô
    "93e61235", # Phân tích môi trường bên ngoài
    "0d254ce6", # Cung cầu và giá cả thị trường
    "c46c6220", # Tổng quan về kinh tế vi mô
    "98750d89", # Ngoại ứng và hàng hóa công cộng
    "29c9ffd6", # Lời mở đầu - Quản trị chiến lược
    "bf83f4b8", # Độ co giãn của cung cầu
    "399fd22d", # Thiết kế cấu trúc tổ chức và hệ thống kiểm soát
    "44f11c34", # Tạo dựng lợi thế cạnh tranh thông qua các chiến lược chức năng
    "6c2d9dd8"  # Chiến lược công ty
]

BASE_URL = "https://voer.edu.vn/m/_/{}"
OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\economics_micro_voer.json"

def crawl():
    results = []
    print(f"Starting crawl for {len(IDS)} documents...")
    
    for i, doc_id in enumerate(IDS):
        url = BASE_URL.format(doc_id)
        try:
            print(f"[{i+1}/{len(IDS)}] Fetching {url}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                title = "Unknown Title"
                h1 = soup.find('h1', class_='title-document')
                if not h1: h1 = soup.select_one('.doc_banner_content h1')
                if not h1: h1 = soup.find('h1')
                
                if h1:
                    title = h1.get_text(strip=True)
                
                content_div = soup.select_one('.inner-content')
                if not content_div:
                    content_div = soup.select_one('.forum-post-content')
                
                if content_div:
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
            
        time.sleep(1)

    print(f"crawl finished. Saving {len(results)} items to {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    crawl()

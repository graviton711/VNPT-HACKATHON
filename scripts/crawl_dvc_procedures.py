
import requests
import json
import time
import os
from tqdm import tqdm

URL = "https://thutuc.dichvucong.gov.vn/jsp/rest.jsp"
OUTPUT_FILE = "data/dvc_procedures_raw.json"

# Headers from User's cURL
HEADERS = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Cookie': 'route=1765545113.605.3785.303127; JSESSIONID=DBEDB5EB3BCD0F6EFE9D58C2DABF45A4; TS0115bee1=01f551f5ee9760a6351cb846f35ea87d67a28a7ef34efd035d9f756eb0fe27fa6e1d22ad36e4289474f59767fb7a4faf9f4b590fc56509929913345245aae6a9d8686eeefccef94f3ab442d35e4114f46012aff424',
    'DNT': '1',
    'Origin': 'https://thutuc.dichvucong.gov.vn',
    'Referer': 'https://thutuc.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh.html',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}

def crawl():
    all_procedures = []
    page_index = 1
    record_per_page = 10 
    
    # Base Payload
    base_payload = {
        "service": "procedure_advanced_search_service_v2",
        "provider": "dvcquocgia",
        "type": "ref",
        "recordPerPage": record_per_page,
        "pageIndex": 1,
        "is_connected": 0,
        "keyword": "", 
        "agency_type": "0",
        "impl_agency_id": "-1",
        "object_id": "-1",
        "field_id": "-1",
        "impl_level_id": "-1"
    }

    print("Starting crawl...")
    
    while True:
        base_payload["pageIndex"] = page_index
        
        data_to_send = {
            "params": json.dumps(base_payload)
        }
        
        success = False
        items = []
        
        for attempt in range(3):
            try:
                print(f"Fetching Page {page_index} (Attempt {attempt+1})...", end=" ")
                resp = requests.post(URL, headers=HEADERS, data=data_to_send, timeout=30)
                
                if resp.status_code != 200:
                    print(f"Failed (Status {resp.status_code})")
                    time.sleep(2)
                    continue
                
                items = resp.json()
                success = True
                break
            except Exception as e:
                print(f"Error ({e})")
                time.sleep(2)
                
        if not success:
            print("Failed after 3 attempts. Aborting.")
            break
            
        if not isinstance(items, list):
            print("Response is not a list. Algorithm mismatch.")
            print(items)
            break
            
        if len(items) == 0:
            print("No more items found. Finished.")
            break
            
        count = len(items)
        print(f"Got {count} items.")
        
        all_procedures.extend(items)
        
        if count < record_per_page:
            print("Reached last page.")
            break
        
        if page_index > 200: 
            print("Safety limit reached (200 pages).")
            break
            
        page_index += 1
        time.sleep(0.5) 

    # Save Results
    print(f"Total crawled: {len(all_procedures)}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_procedures, f, ensure_ascii=False, indent=2)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    crawl()

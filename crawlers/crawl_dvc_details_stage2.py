
import requests
import json
import time
import os
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT_FILE = "data/dvc_procedures_raw.json"
OUTPUT_FILE = "data/dvc_procedures_full.json"
URL = "https://thutuc.dichvucong.gov.vn/jsp/rest.jsp"

# Headers from User
HEADERS = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Cookie': 'route=1765545113.605.3785.303127; JSESSIONID=DBEDB5EB3BCD0F6EFE9D58C2DABF45A4; TS0115bee1=01f551f5ee9760a6351cb846f35ea87d67a28a7ef34efd035d9f756eb0fe27fa6e1d22ad36e4289474f59767fb7a4faf9f4b590fc56509929913345245aae6a9d8686eeefccef94f3ab442d35e4114f46012aff424',
    'DNT': '1',
    'Origin': 'https://thutuc.dichvucong.gov.vn',
    'Referer': 'https://thutuc.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh.html',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
    'X-Requested-With': 'XMLHttpRequest'
}

def fetch_details(item):
    try:
        proc_id = item.get("ID")
        if not proc_id: return item
        
        # 1. Fetch Steps (Trình tự)
        payload_steps = {
            "service": "procedure_get_impl_orders_by_proc_id_service_v2",
            "provider": "dvcquocgia",
            "type": "ref",
            "id": proc_id,
            "parent_id": ""
        }
        res1 = requests.post(URL, headers=HEADERS, data={"params": json.dumps(payload_steps)}, timeout=20)
        if res1.status_code == 200:
            steps = res1.json()
            # Combine content if multiple steps
            steps_text = "\n".join([s.get("CONTENT", "") for s in steps]) if isinstance(steps, list) else ""
            item["STEPS"] = steps_text
        
        # 2. Fetch Requirements (Thành phần hồ sơ)
        # Note: Sometimes requires 'procedure_get_requires_by_procedure_id_service_v2'
        payload_reqs = {
            "service": "procedure_get_requires_by_procedure_id_service_v2",
            "provider": "dvcquocgia",
            "type": "ref",
            "id": proc_id,
            "parent_id": ""
        }
        res2 = requests.post(URL, headers=HEADERS, data={"params": json.dumps(payload_reqs)}, timeout=20)
        if res2.status_code == 200:
             reqs = res2.json()
             reqs_text = "\n".join([r.get("REQUIRE_NAME", "") for r in reqs]) if isinstance(reqs, list) else ""
             item["REQUIREMENTS"] = reqs_text
             
        # Small delay to be polite
        time.sleep(0.1)
        return item
        
    except Exception as e:
        # print(f"Error {proc_id}: {e}")
        return item # Return original item even if detail fetch fails

def main():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found.")
        return

    print("Loading raw procedures...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} items. Fetching details (Threaded)...")
    
    full_data = []
    # Use 8 workers to balance speed vs WAF risk
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_details, item): item for item in data}
        
        for future in tqdm(as_completed(futures), total=len(data)):
             res = future.result()
             full_data.append(res)
             
    # Save
    print(f"Saving {len(full_data)} items to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    print("Done.")

if __name__ == "__main__":
    main()

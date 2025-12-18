
import requests
import json

URL = "https://thutuc.dichvucong.gov.vn/jsp/rest.jsp"

# Original payload from user's JSON + probe
payload_dict = {
    "service": "procedure_advanced_search_service_v2",
    "provider": "dvcquocgia",
    "type": "ref",
    "recordPerPage": 5,
    "pageIndex": 1,
    "is_connected": 0,
    "keyword": "",
    "agency_type": 1,
    "impl_agency_id": -1,
    "object_id": -1,
    "field_id": -1,
    "impl_level_id": -1
}

# Logic from ApiService.js: objJson.params = JSON.stringify(jsonData);
# Default jQuery $.ajax contentType is application/x-www-form-urlencoded
final_data = {
    "params": json.dumps(payload_dict)
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Origin": "https://thutuc.dichvucong.gov.vn",
    "Referer": "https://thutuc.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh.html"
}


print(f"Testing URL: {URL}")
try:
    s = requests.Session()
    s.headers.update(headers)
    
    # 1. Visit main page to get cookies
    print("Visiting main page to establish session...")
    s.get("https://thutuc.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh.html", timeout=15)
    print("Session cookies:", s.cookies.get_dict())

    # 2. POST to API
    resp = s.post(URL, data=final_data, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type')}")
    print("Response Preview:")
    print(resp.text[:500])
    
    if resp.status_code == 200:
        try:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0 and "PROCEDURE_NAME" in data[0]:
                print("SUCCESS! Found procedures.")
                print(f"First 1: {data[0]['PROCEDURE_NAME']}")
            else:
                print("Response valid JSON but unexpected content.")
        except:
             print("Response not valid JSON.")

except Exception as e:
    print(f"Error: {e}")


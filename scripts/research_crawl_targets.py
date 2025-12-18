import requests
from bs4 import BeautifulSoup

def check_luatvietnam():
    print("--- Checking LuatVietnam ---")
    url = "https://luatvietnam.vn/co-cau-to-chuc/nghi-quyet-1656-nq-ubtvqh15-2025-sap-xep-don-vi-hanh-chinh-cap-xa-ha-noi-403020-d1.html"
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find(id='noidung')
            if content:
                text = content.get_text().strip()
                print(f"Content found (length {len(text)}): {text[:100]}...")
            else:
                print("Element id='noidung' not found or empty.")
                # Check for login requirement
                if "Vui lòng đăng nhập" in response.text:
                    print("Login required detected.")
        else:
            print("Failed to access.")
    except Exception as e:
        print(f"Error: {e}")

def check_vbpl():
    print("\n--- Checking VBPL ---")
    # Search for "sắp xếp đơn vị hành chính"
    url = "https://vbpl.vn/pages/timkiem.aspx?Keyword=s%E1%BA%AFp+x%E1%BA%BFp+%C4%91%C6%A1n+v%E1%BB%8B+h%C3%A0nh+ch%C3%ADnh"
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            if "sắp xếp đơn vị hành chính" in response.text:
                 print("Search query reflected in page.")
            else:
                 print("Search query NOT reflected (might be dynamic loading).")
            
            # Try to fetch a detail page if possible (need a real URL, but search is good first step)
        else:
            print("Failed to access VBPL.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_luatvietnam()
    check_vbpl()

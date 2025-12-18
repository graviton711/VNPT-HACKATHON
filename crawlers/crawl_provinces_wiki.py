import wikipediaapi
import json
import time
import os
import re
import concurrent.futures
import threading

# --- CẤU HÌNH ---
PROVINCES = [
    "An Giang", "Bà Rịa – Vũng Tàu", "Bạc Liêu", "Bắc Giang", "Bắc Kạn", "Bắc Ninh", 
    "Bến Tre", "Bình Dương", "Bình Định", "Bình Phước", "Bình Thuận", "Cà Mau", 
    "Cao Bằng", "Cần Thơ", "Đà Nẵng", "Đắk Lắk", "Đắk Nông", "Điện Biên", 
    "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang", "Hà Nam", "Hà Nội", 
    "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang", "Hòa Bình", "Hưng Yên", 
    "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu", "Lâm Đồng", "Lạng Sơn", 
    "Lào Cai", "Long An", "Nam Định", "Nghệ An", "Ninh Bình", "Ninh Thuận", 
    "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", 
    "Quảng Trị", "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên", 
    "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", "Trà Vinh", "Tuyên Quang", 
    "Vĩnh Long", "Vĩnh Phúc", "Yên Bái", "Thành phố Hồ Chí Minh"
]

EXCLUDE_SECTIONS = [
    r"Xem thêm", r"Tham khảo", r"Chú thích", r"Liên kết ngoài", r"Thư mục", r"Ghi chú", r"Nguồn"
]

OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\provinces_wiki_dated.json"
MAX_WORKERS = 8  # Số luồng chạy song song
print_lock = threading.Lock() # Khóa để in log không bị đè nhau

# --- XỬ LÝ NGÀY THÁNG ---
def extract_dates(text):
    """Trích xuất các mốc thời gian từ văn bản."""
    dates = set()
    patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
        r'ngày \d{1,2} tháng \d{1,2} năm \d{4}',
        r'tháng \d{1,2} năm \d{4}',
        r'năm \d{4}',
        r'\b\d{4}\b',
        r'thế kỷ \w+',
        r'thế kỷ \d+'
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for date in matches:
            dates.add(date)
    return sorted(list(dates))

# --- HÀM XỬ LÝ CHÍNH ---
def get_page_content(wiki, page_title):
    candidates = [
        f"{page_title} (tỉnh)",
        f"{page_title} (thành phố trực thuộc trung ương)", 
        page_title
    ]
    
    if page_title in ["Hà Nội", "Hồ Chí Minh", "Hải Phòng", "Đà Nẵng", "Cần Thơ", "Thành phố Hồ Chí Minh"]:
        candidates = [page_title, f"Thành phố {page_title}"]
        if "Hồ Chí Minh" in page_title: candidates = ["Thành phố Hồ Chí Minh"]

    for cand in candidates:
        page = wiki.page(cand)
        if page.exists():
            summary_lower = page.summary.lower()
            if "có thể đề cập đến" in summary_lower or "có thể là" in summary_lower:
                continue 
            return page, page.title
    return None, None

def process_sections_recursively(sections, parent_titles=[], level=0):
    segments = []
    for s in sections:
        is_excluded = False
        for p in EXCLUDE_SECTIONS:
            if re.search(p, s.title, re.IGNORECASE):
                is_excluded = True
                break
        if is_excluded: continue

        current_titles = parent_titles + [s.title]
        section_path = " > ".join(current_titles)

        paragraphs = s.text.split('\n')
        for p in paragraphs:
            p = p.strip()
            if not p: continue
            
            segments.append({
                "section_path": section_path,
                "level": level,
                "content": p,
                "temporal_tags": extract_dates(p)
            })
        
        child_segments = process_sections_recursively(s.sections, current_titles, level + 1)
        segments.extend(child_segments)
    return segments

# --- WORKER CHO TỪNG LUỒNG ---
def process_single_province(p_name):
    # Khởi tạo instance Wiki riêng cho mỗi luồng để tránh xung đột session
    wiki = wikipediaapi.Wikipedia(
        user_agent='VNPT_Hackathon_Bot/1.2 (contact: admin@vnpt.vn)',
        language='vi',
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )
    
    try:
        page, real_title = get_page_content(wiki, p_name)
        
        if page:
            province_data = {
                "province": p_name,
                "wiki_title": real_title,
                "url": page.fullurl,
                "segments": []
            }
            
            # Summary
            for p in page.summary.split('\n'):
                if p.strip():
                    province_data["segments"].append({
                        "section_path": "Giới thiệu chung",
                        "level": 0,
                        "content": p.strip(),
                        "temporal_tags": extract_dates(p)
                    })
            
            # Sections
            sections_segments = process_sections_recursively(page.sections)
            province_data["segments"].extend(sections_segments)
            
            with print_lock:
                print(f"[OK] {p_name} -> {real_title} ({len(province_data['segments'])} segments)")
            
            return province_data
        else:
            with print_lock:
                print(f"[NOT FOUND] {p_name}")
            return None
            
    except Exception as e:
        with print_lock:
            print(f"[ERROR] {p_name}: {e}")
        return None

# --- MAIN CONTROLLER ---
def crawl_multithreaded():
    print(f"Starting crawl with {MAX_WORKERS} threads for {len(PROVINCES)} provinces...")
    start_time = time.time()
    
    data = []
    
    # Sử dụng ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Map từng tỉnh vào hàm xử lý
        results = executor.map(process_single_province, PROVINCES)
        
        # Thu thập kết quả
        for res in results:
            if res:
                data.append(res)
    
    # Lưu file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    duration = time.time() - start_time
    print(f"\nCompleted in {duration:.2f} seconds.")
    print(f"Saved {len(data)} provinces to {OUTPUT_FILE}")

if __name__ == "__main__":
    crawl_multithreaded()
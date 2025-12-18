import json
import re
import os
from datetime import datetime

def clean_text(text):
    if not text:
        return ""
    # Remove excessive newlines and whitespace
    return re.sub(r'\n+', '\n', text).strip()

def clean_content(text):
    if not text:
        return ""
    
    lines = text.split('\n')
    cleaned_lines = []
    
    # Garbage phrases to filter out strictly (entire line match or sidebar noise)
    garbage_phrases = ["đang theo dõi", "bổ sung", "hiệu lực", "tình trạng hiệu lực", "đã biết", "xem chi tiết", "tải về", "in bài viết"]
    
    # Heuristic: Find start of document (Skip initial garbage headers)
    start_idx = 0
    for i, line in enumerate(lines[:30]):
        line_upper = line.strip().upper()
        if "CỘNG HÒA" in line_upper or "CHÍNH PHỦ" in line_upper or "QUỐC HỘI" in line_upper or "NGHỊ ĐỊNH" in line_upper or re.match(r'^SỐ:\s*\d+', line_upper):
            start_idx = i
            break
            
    # Process lines from start_idx onwards
    for line in lines[start_idx:]:
        line_strip = line.strip()
        if not line_strip:
            cleaned_lines.append("") # Preserve paragraph breaks
            continue
            
        # Filter out garbage lines
        line_lower = line_strip.lower()
        is_garbage = False
        for phrase in garbage_phrases:
            if line_lower == phrase or line_lower.startswith("tình trạng hiệu lực:") or line_lower.startswith("hiệu lực:"):
                is_garbage = True
                break
        
        if not is_garbage:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()

def parse_date(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Check for crawler garbage
    if "Đăng nhập" in date_str or "Đã biết" in date_str:
        return None
        
    date_str = date_str.strip()
    # Try common formats
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None

def get_year(date_str):
    if not date_str:
        return None
    try:
        return int(date_str.split('/')[-1])
    except:
        return None

def normalize_metadata_key(key):
    # Normalize keys like "Ngày ban hànhNgày ban hành là..." to "issuance_date"
    key_lower = key.lower()
    if "ngày ban hành" in key_lower:
        return "issuance_date"
    if "áp dụng" in key_lower or "ngày hiệu lực" in key_lower or "có hiệu lực" in key_lower:
        return "effective_date"
    return None

def main():
    input_path = "data/decrees_corpus_cleaned.json"
    output_path = "data/decrees_corpus_final.json"
    
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        return

    print(f"Reading {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cleaned_data = []
    print(f"Processing {len(data)} items...")

    for item in data:
        # The file is already flat, so we just copy and clean content
        cleaned_item = item.copy()
        
        # Apply the strong cleaning key
        cleaned_item["content"] = clean_content(item.get("content"))
        cleaned_item["title"] = clean_text(item.get("title"))

        cleaned_data.append(cleaned_item)

    print(f"Saving {len(cleaned_data)} cleaned items to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    print("Done.")

if __name__ == "__main__":
    main()

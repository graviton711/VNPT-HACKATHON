
import pdfplumber
import collections
import re
import os

# Common Vietnamese Words (Dictionary)
COMMON_WORDS = {
    "và", "của", "là", "có", "những", "cho", "người", "trong", "ác",
    "không", "các", "một", "này", "với", "để", "làm", "đã", "từ",
    "được", "rằng", "lại", "về", "nhân", "dân", "hồ", "chí", "minh",
    "nước", "hội", "nam", "đảng", "bác", "sự", "bộ", "chủ", "tịch",
    "cách", "mạng", "ra", "vào", "năm", "khi", "ngày", "tháng",
    "đến", "chúng", "ta", "thì", "mà", "nhiều", "hơn", "như", "việt",
    "đồng", "bào", "chiến", "sĩ", "quân", "đội", "công", "tác",
    "yêu", "tổ", "quốc", "hòa", "bình", "thống", "nhất", "độc", "lập",
    "tự", "do", "hạnh", "phúc", "lời", "giới", "thiệu", "toàn", "tập",
    "sản", "xuất", "phát", "triển", "kinh", "tế", "văn", "hóa",
    "thanh", "niên", "phụ", "nữ", "thiếu", "nhi", "nhiđồng",
    "chính", "phủ", "quốc", "gia", "thế", "giới", "chủ", "nghĩa",
    "xã", "hội", "cộng", "sản", "tư", "bản", "đế", "quốc",
    "thực", "dân", "phong", "kiến", "giai", "cấp", "đấu", "tranh",
    "cần", "kiệm", "liêm", "chính", "kháng", "chiến", "kiến", "quốc",
    "khó", "khăn", "gian", "khổ", "thắng", "lợi", "vẻ", "vang",
    "lịch", "sử", "thời", "đại", "mới", "hà", "nội", "sài", "gòn",
    "huế", "đà", "nẵng", "hải", "phòng", "cần", "thơ", "lạng", "sơn",
    "cao", "bằng", "tuyên", "quang", "thái", "nguyên", "phú", "thọ",
    "bắc", "trung", "liên", "xô", "trung", "quốc", "lào", "campuchia",
    "pháp", "nhật", "mỹ", "anh", "đức", "ý", "nga",
    "mười", "trăm", "nghìn", "triệu", "tỷ", "thứ", "ba", "tư", "năm",
    "sáu", "bảy", "tám", "chín", "mấy", "bao", "nhiêu", "bấy", "nhiêu",
    "chưa", "bao", "giờ", "luôn", "luôn", "tất", "cả", "mọi",
    "vì", "nếu", "nhưng", "tuy", "bởi", "do", "nên", "vậy",
    "cũng", "đều", "sẽ", "đang", "vẫn", "cứ", "chỉ", "mới",
    "rất", "lắm", "quá", "hơi", "khá", "thật", "sự", "quả", "nhiên",
    "tuyệt", "đối", "hoàn", "toàn", "nhất", "định", "phải", "cần",
    "muốn", "thích", "yêu", "ghét", "sợ", "lo", "mừng", "vui",
    "buồn", "giận", "thương", "nhớ", "quên", "biết", "hiểu", "nghĩ",
    "nói", "viết", "đọc", "nghe", "nhìn", "thấy", "xem", "ăn", "uống",
    "ngủ", "nghỉ", "đi", "đứng", "ngồi", "nằm", "chạy", "nhảy",
    "mang", "vác", "đem", "lấy", "bỏ", "giữ", "cho", "biếu", "tặng",
    "dùng", "sử", "dụng", "lợi", "dụng", "áp", "dụng", "thực", "hiện",
    "tiến", "hành", "tham", "gia", "tổ", "chức", "lãnh", "đạo", "chỉ", "huy",
    "giáo", "dục", "đào", "tạo", "huấn", "luyện", "học", "tập", "nghiên", "cứu",
    "lao", "động", "làm", "việc", "công", "nhân", "nông", "dân", "trí", "thức"
}

# PDF Path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_FILE = os.path.join(BASE_DIR, "pdf_data", "HCM TOAN TAP", "HO-CHI-MI_636854714264142695.pdf")

def main():
    print(f"Reading {PDF_FILE}...")
    text = ""
    try:
        with pdfplumber.open(PDF_FILE) as pdf:
            # Read first 10 pages for sample
            for i, page in enumerate(pdf.pages[:10]):
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return

    # 1. Identify "Cipher" Words (words with char > 128)
    words = re.split(r'\s+', text)
    cipher_words = []
    
    # Track raw char usage
    raw_chars = collections.Counter()
    
    for w in words:
        # Keep punctuation attached? No, better strip for word matching
        clean_w = w.strip(".,;:?!\"'()[]{}")
        if any(ord(c) > 128 for c in clean_w):
            cipher_words.append(clean_w)
            for c in clean_w:
                if ord(c) > 128:
                    raw_chars[c] += 1
    
    print(f"Found {len(cipher_words)} cipher word tokens.")
    print(f"Unique high-bit chars: {len(raw_chars)}")
    print("Top 10 raw chars:", [f"{c}({ord(c)})" for c, _ in raw_chars.most_common(10)])

    # 2. Solver Loop
    # We want to find a map `mapping: char -> unicode_char`
    mapping = {}
    
    # Pre-seed with obvious ASCII map (redundant but safe)
    # TCVN3 typically maps ASCII to ASCII.
    
    # Set of known Vietnamese characters to map TO
    viet_chars = set("àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ")
    
    # Heuristic: Find "almost ASCII" words.
    # e.g., "H[x]" -> "Hồ".
    
    resolved_count = 0
    possible_matches = collections.defaultdict(list) # char -> list of candidate suggestions

    loop_limit = 10
    for loop in range(loop_limit):
        print(f"--- Loop {loop+1} ---")
        updates = 0
        
        for w in cipher_words:
            # Apply current known mapping
            partial = list(w)
            unknown_indices = []
            for idx, c in enumerate(partial):
                if c in mapping:
                    partial[idx] = mapping[c]
                elif ord(c) > 128:
                    unknown_indices.append(idx)
            
            partial_str = "".join(partial)
            
            if not unknown_indices:
                continue

            # If only 1 unknown char, try to match against dictionary
            if len(unknown_indices) == 1:
                idx = unknown_indices[0]
                raw_char = w[idx]
                
                # Check regex match against dictionary
                # Construct regex: replace the unknown char with "."
                pattern_str = "^" + partial_str[:idx] + "(.)" + partial_str[idx+1:] + "$"
                # But we only care about Vietnamese range matches
                
                # Let's brute force valid words from dictionary that match strict template
                # e.g. "H." matches "Hồ", "Hà", "Hè"...
                
                candidates = []
                for valid_word in COMMON_WORDS:
                    if len(valid_word) == len(partial_str):
                        match_flag = True
                        captured = None
                        for i, (p_c, v_c) in enumerate(zip(partial_str, valid_word)):
                            if i == idx:
                                captured = v_c
                            elif p_c != v_c:
                                match_flag = False
                                break
                        if match_flag and captured:
                            candidates.append(captured)
                
                if candidates:
                    # Vote
                    for cand in candidates:
                         possible_matches[raw_char].append(cand)

        # Process votes
        for raw_c, suggestions in possible_matches.items():
            if raw_c in mapping: continue
            
            counts = collections.Counter(suggestions)
            best_cand, count = counts.most_common(1)[0]
            
            # Confidence threshold? 
            # If "H[x]" -> "Hồ" (10 times) and "H[x]" -> "Hà" (1 time), pick "Hồ".
            if count > 2:
                print(f"SOLVED: '{raw_c}' ({ord(raw_c)}) -> '{best_cand}' (Votes: {dict(counts)})")
                mapping[raw_c] = best_cand
                updates += 1
        
        possible_matches.clear()
        
        if updates == 0:
            print("No new updates found.")
            break

    # 3. Print Final Map
    # 3. Print Final Map
    output_path = os.path.join(BASE_DIR, "data", "inferred_map_result.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("FINAL_MAP = {\n")
        sorted_map = sorted(mapping.items(), key=lambda x: ord(x[0]))
        for k, v in sorted_map:
            f.write(f"    {repr(k)}: {repr(v)}, # {ord(k)}\n")
        f.write("}\n")
    
    print(f"Map saved to {output_path}")

    # Verify coverage
    print("\n--- SAMPLE DECODE ---")
    
    decoded_example = []
    
    for w in cipher_words[:50]:
        res = []
        for c in w:
            res.append(mapping.get(c, c)) # fallback to raw if not found
        decoded_example.append("".join(res))
        
    print(" ".join(decoded_example))

if __name__ == "__main__":
    main()

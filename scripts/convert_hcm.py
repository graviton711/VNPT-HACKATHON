import pdfplumber
import json
import os
import glob
import re
from tqdm import tqdm

# Hardcoded reliable TCVN3 -> Unicode Map based on inspection
# 0xA9 (169) -> â
# 0xCB (203) -> ậ
# 0xB9 (185) -> ạ
# 0xB8 (184) -> á
# 0xB6 (182) -> ả
# 0xA4 (164) -> Ô (context "KHÔNG")
# 0xE3 (227) -> ó (context "Có")
# 0xD7 (215) -> ì (context "Gì")
# 0xFD (253) -> ý (context "Quý")
# 0xA5 (165) -> Ơ (context "HƠN")
# 0xA7 (167) -> Đ (context "ĐỘC")
# 0xE9 (233) -> Ộ (context "ĐỘC") ? Wait. "ĐéC" -> ĐỘC. 
# 0xCB (203) -> Ậ (context "LẬP") (Wait, 0xCB is ậ lowercase?)
# 0xF9 (249) -> Ự (context "TỰ")

# Final Hybrid TCVN3 Map (Solver + Manual Overrides)
TCVN3_MAP = {
    # Base Solver Output
    '\xa7': 'đ', # §
    '\xa8': 'ă', # ¨
    '\xa9': 'â', # ©
    '\xaa': 'ê', # ª
    '\xab': 'ô', # «
    '\xac': 'ơ', # ¬
    '\xae': 'đ', # ®
    '\xb5': 'à', # µ
    '\xb6': 'ả', # ¶
    '\xb7': 'ã', # ·
    '\xb8': 'á', # ¸
    # '\xb9': 'i', # Solver wrong
    '\xb9': 'ạ', # Manual Correct
    '\xbc': 'ô', # ¼
    '\xbe': 'ắ', # ¾
    '\xc7': 'ấ', # Ç
    '\xca': 'ấ', # Ê
    '\xcb': 'ậ', # Ë
    # '\xd0': 'a', # Solver wrong
    '\xd0': 'é', # Manual Correct ("khéo")
    '\xd2': 'ề', # Ò
    '\xd3': 'ế', # Ó
    '\xd5': 'ế', # Õ
    '\xd6': 'ệ', # Ö
    '\xd7': 'ì', # ×
    '\xd8': 'ỉ', # Ø
    '\xdc': 'ĩ', # Ü
    '\xdd': 'í', # Ý
    '\xde': 'ị', # Þ
    '\xdf': 'ò', # ß
    '\xe2': 'õ', 
    '\xe3': 'ó', # ã
    '\xe4': 'ọ', # ä
    '\xe5': 'ồ', # å (Manual: Hồ)
    '\xe8': 'ố', # è
    '\xe9': 'ộ', # é
    '\xea': 'ờ', # ê
    # '\xeb': 'ý', # Solver said 'ý'. Context "ý Nam Trực" -> Impossible. "ở Nam Trực" -> Correct.
    '\xeb': 'ở',   # ë -> ở
    '\xed': 'ấ',   # í (Collision with ớ)
    
    '\xee': 'ợ', # î
    '\xef': 'ọ', # ï (Standard 'ớ'. Solver 'ọ'. "học" -> "h\xefc"? Plausible.)
    '\xf1': 'ủ', # ñ
    '\xf2': 'à', # ò (Standard 'ũ'. Solver 'à'. "và" -> "v\xf2"?)
    '\xf3': 'ú', # ó
    '\xf4': 'à', # ô (Standard 'ụ'. Solver 'à'. "là" -> "l\xf4"?)
    '\xf7': 'ữ', # ÷
    '\xf8': 'ứ', # ø
    '\xf9': 'ự', # ù
    '\u2212': 'ư', # −
    
    # Final patches
    '\xe6': 'ổ',   # æ -> ổ ("tổng")
    '\xfe': 'ỳ',   # þ (added for "bất kỳ")
    'ê': 'ờ',      # ê -> ờ ("lời")
}

# Explicit word fixes for collisions that single-char mapping cannot solve
REPLACEMENT_PAIRS = {
    # Mistranslations due to char collisions
    "giấi": "giới",
    "Giấi": "Giới",
    "gií": "giới",
    
    # "bất", "nhất", "tất" often appear as "bấ", "nhấ", "tấ" if 't' is encoded in the vowel or dropped
    "bấ kỳ": "bất kỳ",
    "nhấ định": "nhất định",
    "nhấ trí": "nhất trí",
    "tấ cả": "tất cả",
    "tấ nhiên": "tất nhiên",
    
    # Fix "nước", "trước", "bước" (Collision \xed -> ấ. "ư" + "ớc" -> "ư" + "ấc" -> "ưấc")
    "ưấc": "ước",
    "nưấc": "nước",
    "trưấc": "trước",
    "bưấc": "bước",
    "Nưấc": "Nước",
    
    # "khéo"
    "khđo": "khéo",
    
    # "cùng"
    "cèng": "cùng",
    "cọng": "cùng",
    "cống": "cùng", # Aggressive for HCM corpus context
    "Cèng": "Cùng",
    "Cọng": "Cùng",
    
    # "lời"
    "lờ giới": "lời giới", # "lê giới" -> "lờ giới".
    "trả lờ ": "trả lời ",
    
    # Textual cleanups
    "Hô Chí Minh": "Hồ Chí Minh",
    "Hô Chủ tịch": "Hồ Chủ tịch",
    "Gi¬nev¬": "Giơnevơ",
}

def tcvn3_to_unicode(text):
    if not text: return ""
    res = []
    for char in text:
        res.append(TCVN3_MAP.get(char, char))
    
    final_text = "".join(res)
    
    # 1. Apply Atomic Fixes first (e.g. chars that became single tokens)
    # Contextual Logic for "giấ" -> "giới"
    final_text = final_text.replace("giấ ", "giới ")
    final_text = final_text.replace("giấi", "giới")
    final_text = final_text.replace("Giấi", "Giới")
    
    # 2. Apply Word-level / Phrase fixes
    for bad, good in REPLACEMENT_PAIRS.items():
        if bad in final_text:
            final_text = final_text.replace(bad, good)
            
    # Recursive pass? Just one pass should be enough if ordered well.
    # Check "lờ giới" again just in case it was created by a later step? 
    # (No, "giới" is fixed in step 1. "lờ" comes from map. So step 2 sees "lờ giới".)
    
    return final_text

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PDF_DIR = os.path.join(BASE_DIR, 'pdf_data', 'HCM TOAN TAP')
OUTPUT_FILE = os.path.join(BASE_DIR, 'data', 'hcm_complete.json')

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def process_file(pdf_path):
    print(f"Processing: {os.path.basename(pdf_path)}")
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                # Basic header filter
                lines = t.split('\n')
                filtered = []
                for line in lines:
                   # Skip running headers
                   if "hå chÝ minh toµn tËp" in line.lower(): continue 
                   if re.match(r'^\d+$', line.strip()): continue
                   filtered.append(line)
                full_text += "\n".join(filtered) + "\n"
    
    # Identify Volume Name from file or text?
    # Filename is obscure. Let's assume Volume info is in first few lines or we just use filename.
    # The user manual mentioned "HCM Toan Tap" -> "Tap X". 
    # Let's inspect the first page text for "tËp 15" pattern to guess volume.
    vol_match = re.search(r'tËp\s+(\d+)', full_text, re.IGNORECASE)
    vol_name = f"Tập {vol_match.group(1)}" if vol_match else "Hồ Chí Minh Toàn Tập"

    # Convert WHOLE text first
    decoded_text = tcvn3_to_unicode(full_text)
    
    # SPLIT ARTICLES
    # Pattern: 
    # 1. Newline
    # 2. Number (optional)
    # 3. UPPERCASE TITLE
    # 4. Content
    # 5. "Hồ Chí Minh" signature (End of article)
    
    # Actually, inspection showed "1 \n TITLE". 
    # Let's try splitting by regex: `^\d+\s*$` (line with only number) followed by `^[UPPERCASE]`
    
    # Or simpler: Split by "Hồ Chí Minh" signature at the end?
    # But some might not have it.
    
    # Heuristic: Uppercase lines that are short (< 100 chars) are Titles.
    # We iterate lines.
    
    lines = decoded_text.split('\n')
    dataset = []
    
    current_title = "Giới thiệu chung"
    current_buffer = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Check if Title
        # 1. Uppercase
        # 2. Short
        # 3. Not just a number
        # 4. Not "Hồ Chí Minh" (Signature)
        if line.isupper() and len(line) < 150 and len(line) > 5 and "HỒ CHÍ MINH" not in line:
            # Save previous
            if current_buffer:
                body = "\n".join(current_buffer)
                if len(body) > 100: # Filter noise
                    dataset.append({
                        "full_title": f"Hồ Chí Minh Toàn Tập > {vol_name} > {current_title}",
                        "text": f"{current_title}\n{body}",
                        "source": os.path.basename(pdf_path)
                    })
            current_title = clean_text(line)
            current_buffer = []
        else:
            current_buffer.append(line)
            
    # Flush last
    if current_buffer:
        body = "\n".join(current_buffer)
        if len(body) > 100:
             dataset.append({
                "full_title": f"Hồ Chí Minh Toàn Tập > {vol_name} > {current_title}",
                "text": f"{current_title}\n{body}",
                "source": os.path.basename(pdf_path)
            })
            
    return dataset

import concurrent.futures

def main():
    files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    all_data = []
    
    max_workers = 8
    print(f"Starting parallel processing with {max_workers} workers...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(process_file, f): f for f in files}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_file), total=len(files), desc="Converting PDFs"):
            f = future_to_file[future]
            try:
                chunks = future.result()
                all_data.extend(chunks)
            except Exception as e:
                print(f"Error {f}: {e}")
            
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"Done. Saved {len(all_data)} articles to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

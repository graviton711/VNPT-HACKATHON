import pdfplumber
import json
import re
import os
import glob
import sys
from operator import itemgetter

PDF_DIR = os.path.join("pdf_data", "KythuaDoluong")
OUTPUT_PATH = os.path.join("data", "ky_thuat_do_luong_structured.json")

# Regex Patterns (Reused from HCM logic)
RE_CHAPTER = re.compile(r"^(CHƯƠNG|Chương)\s+([IVX0-9]+)(.*)", re.IGNORECASE)
RE_ROMAN = re.compile(r"^([IVX]+)\.\s+(.*)") # I. Title
RE_NUMBER = re.compile(r"^(\d+)\.\s+(.*)")    # 1. Title
RE_LETTER = re.compile(r"^([a-z])[\)\.]\s+(.*)") # a) Title or a. Title

def clean_doubled_text(text: str) -> str:
    """
    Heuristic to fix 'CCHHƯƯƠƠNNGG' -> 'CHƯƠNG'.
    If > 40% of characters are identical to the previous one, assume it's a doubled-printing artifact.
    """
    if not text or len(text) < 3:
        return text
        
    doubles = 0
    for i in range(1, len(text)):
        if text[i] == text[i-1]:
            doubles += 1
            
    ratio = doubles / len(text)
    
    if ratio > 0.4:
        return "".join(c for i, c in enumerate(text) if i == 0 or c != text[i-1])
        
    return text

def extract_text_with_formulas(page):
    """
    Custom text extractor to detect superscripts/subscripts and basic layout.
    """
    chars = page.chars
    if not chars:
        return ""

    # Sort characters by vertical position (top), then horizontal (x0)
    chars.sort(key=itemgetter('top', 'x0'))
    
    clusters = []
    current_cluster = []
    
    # Clustering logic: Group characters that are on likely the same line.
    # We use a threshold. If the vertical distance to the previous char is large, start new line.
    # But superscripts are slightly offset. We should look at 'bottom' and 'top' overlap.
    
    if not chars: return ""

    current_cluster = [chars[0]]
    
    for char in chars[1:]:
        last_char = current_cluster[-1]
        
        # Heuristic: If vertical overlap is significant, same line.
        # Or if centroids are close.
        # Let's use a simpler heuristic for now: Top diff > 5.
        
        # Note: PDF 'top' is distance from top of page.
        diff = abs(char['top'] - last_char['top'])
        
        # If diff > 10 (approx half a line height usually), treat as new line
        # This might break if superscript is REALLY high, but usually it's within 3-5 pts.
        if diff > 8: 
            # Check context: is it just a char far to the right but same line?
            # If x is also far back (start of new line), yes.
            # But we sorted by top mainly.
            clusters.append(current_cluster)
            current_cluster = [char]
        else:
            current_cluster.append(char)
            
    clusters.append(current_cluster)
    
    full_text = []
    
    for line_chars in clusters:
        # Sort by x0 to read left-to-right
        line_chars.sort(key=itemgetter('x0'))
        
        # 1. Filter exact duplicates (same x0, same top, same text) - handles some doubling issues at source
        # But we must be careful not to remove 'l' 'l' in 'hello'.
        unique_chars = []
        if line_chars:
            unique_chars.append(line_chars[0])
            for c in line_chars[1:]:
                prev = unique_chars[-1]
                # If same char at almost same position (< 1pt), skip
                if c['text'] == prev['text'] and abs(c['x0'] - prev['x0']) < 1 and abs(c['top'] - prev['top']) < 1:
                    continue
                unique_chars.append(c)
        line_chars = unique_chars

        if not line_chars: continue

        # Determine baseline metrics from the most common size/top
        sizes = [c['size'] for c in line_chars]
        if not sizes: continue
        
        # Base size = most frequent size
        base_size = max(set(sizes), key=sizes.count)
        
        # Base top: Median 'top' of characters matching base_size
        base_candidates = [c['top'] for c in line_chars if abs(c['size'] - base_size) < 1]
        if not base_candidates: base_candidates = [c['top'] for c in line_chars]
        
        base_candidates.sort()
        base_top = base_candidates[len(base_candidates)//2]
        
        line_str = ""
        last_x1 = line_chars[0]['x0'] # Init
        
        for i, char in enumerate(line_chars):
            # Space detection
            # If distance from prev char end > specific threshold, insert space
            if i > 0:
                gap = char['x0'] - last_x1
                # Threshold: usually width of a space char or ~1/4 em. 
                # Let's guess 3 pts or 0.3 * size
                if gap > max(2, char['size'] * 0.3):
                    line_str += " "
            
            text = char['text']
            # Ignore placeholder chars or weird control chars if any
            
            # Super/Sub logic
            is_small = char['size'] < base_size * 0.95
            
            # Allow some tolerance for 'top' equality
            top_diff = char['top'] - base_top
            
            # PDF Coord: Top=0 is top of page.
            # Superscript: Higher up -> Smaller 'top' value -> top_diff < 0 (negative)
            # Subscript: Lower down -> Larger 'top' value -> top_diff > 0 (positive)
            
            # We enforce a threshold. e.g. > 1/10th of fontSize vertical offset
            threshold = base_size * 0.15
            
            if is_small:
                if top_diff < -threshold:
                    # Superscript
                    # Detect if previous char was also super? e.g. 10^-6
                    # For now just strictly mark it.
                    # We strip existing ^ to avoid ^a^2 issues if text extracted had them (unlikely here)
                    text = f"^{text}"
                elif top_diff > threshold:
                    # Subscript
                    text = f"_{text}"
            
            # Heuristic for base-size chars that are shifted? (Math symbols often are)
            # Ignore for now unless obvious.

            line_str += text
            last_x1 = char['x1']
        
        full_text.append(line_str)
        
    return "\n".join(full_text)

def parse_pdfs():
    if not os.path.exists(PDF_DIR):
        print(f"Directory not found: {PDF_DIR}")
        return

    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {PDF_DIR}")
        return
        
    print(f"Found {len(pdf_files)} PDF files in {PDF_DIR}...")
    
    all_structure = []
    
    for pdf_path in sorted(pdf_files):
        print(f"Processing {os.path.basename(pdf_path)}...")
        
        current_meta = {
            "chapter": "",
            "roman": "",
            "number": "",
            "letter": ""
        }
        current_content = []
        last_header_key = None 

        def save_chunk(filename):
            text = "\n".join(current_content).strip()
            if text:
                # Construct meaningful title
                path_parts = []
                if current_meta['chapter']: path_parts.append(current_meta['chapter'])
                if current_meta['roman']: path_parts.append(current_meta['roman'])
                if current_meta['number']: path_parts.append(current_meta['number'])
                if current_meta['letter']: path_parts.append(current_meta['letter'])
                
                full_title = " > ".join(path_parts) if path_parts else os.path.basename(filename)
                
                item = {
                    "metadata": current_meta.copy(),
                    "full_title": full_title,
                    "content": text,
                    "source": os.path.basename(filename)
                }
                all_structure.append(item)

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    # USE CUSTOM EXTRACTOR HERE
                    text = extract_text_with_formulas(page)
                    
                    if not text: continue
                        
                    lines = text.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line: continue

                        # FIX: Clean doubled text (still apply this as fallback)
                        line = clean_doubled_text(line)
                        
                        # PRIORITY: Explicit Regex Check
                        
                        # 1. Chapter
                        match_chap = RE_CHAPTER.match(line)
                        if match_chap:
                            save_chunk(pdf_path)
                            current_content = []
                            current_meta["chapter"] = line
                            current_meta["roman"] = ""
                            current_meta["number"] = ""
                            current_meta["letter"] = ""
                            last_header_key = "chapter"
                            continue
                        
                        # 2. Roman (I.)
                        match_roman = RE_ROMAN.match(line)
                        if match_roman:
                            save_chunk(pdf_path)
                            current_content = []
                            current_meta["roman"] = line
                            current_meta["number"] = ""
                            current_meta["letter"] = ""
                            last_header_key = "roman"
                            continue
                            
                        # 3. Number (1.)
                        match_num = RE_NUMBER.match(line)
                        if match_num:
                            save_chunk(pdf_path)
                            current_content = []
                            current_meta["number"] = line
                            current_meta["letter"] = ""
                            last_header_key = "number"
                            continue
                        
                        # 4. Letter (a.)
                        match_let = RE_LETTER.match(line)
                        if match_let:
                            save_chunk(pdf_path)
                            current_content = []
                            current_meta["letter"] = line
                            last_header_key = "letter"
                            continue

                        # HEURISTIC: Multiline Title Continuation
                        if last_header_key and len(line) > 0 and line[0].islower():
                            current_meta[last_header_key] += " " + line
                            continue
                        
                        # Standard Content
                        current_content.append(line)
                        last_header_key = None
                        
                # Save last chunk of file
                save_chunk(pdf_path)
                
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")

    print(f"Extracted total {len(all_structure)} chunks.")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_structure, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    parse_pdfs()

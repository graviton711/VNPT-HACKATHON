import pdfplumber
import json
import os
import glob
import re
from tqdm import tqdm

# Configuration
# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "pdf_data", "Vietnam_history")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "history_vietnam_complete.json")

# Regex Patterns
# CHƯƠNG [ROMAN/DIGIT] [TITLE]
PAT_CHAPTER = re.compile(r'^\s*CHƯƠNG\s+([IVX0-9]+)(.*)', re.IGNORECASE)
# BÀI [DIGIT] [TITLE]
PAT_LESSON = re.compile(r'^\s*BÀI\s+(\d+)(.*)', re.IGNORECASE)
# [ROMAN]. [TITLE] e.g. I. KHỞI NGHĨA...
PAT_ROMAN = re.compile(r'^\s*([IVX]+)\.\s+(.*)')
# [DIGIT]. [TITLE] e.g. 1. Diễn biến...
PAT_DIGIT = re.compile(r'^\s*(\d+)\.\s+(.*)')
# [LETTER]) [TITLE] e.g. a) Nguyên nhân...
PAT_LETTER = re.compile(r'^\s*([a-z])\)\s+(.*)')

# Constants
MAX_HEADER_LENGTH = 150  # If a line is longer than this, it's likely text, not a header

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def process_single_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    volume_name = filename.split('-')[0].strip()
    
    print(f"Processing: {filename}")
    
    chunks = []
    
    # Hierarchy State
    current_state = {
        "chapter": "",
        "lesson": "",
        "roman": "",
        "digit": "",
        "letter": ""
    }
    
    # Text Buffer
    text_buffer = []
    
    def flush_buffer(page_num):
        nonlocal text_buffer
        content = " ".join(text_buffer).strip()
        if content:
            # Construct breadcrumbs
            hierarchy = []
            if current_state['chapter']: hierarchy.append(current_state['chapter'])
            if current_state['lesson']: hierarchy.append(current_state['lesson'])
            if current_state['roman']: hierarchy.append(current_state['roman'])
            if current_state['digit']: hierarchy.append(current_state['digit'])
            if current_state['letter']: hierarchy.append(current_state['letter'])
            
            full_context_title = " > ".join(hierarchy)
            
            # Create Chunk (Simplified Structure)
            chunk = {
                "full_title": full_context_title,
                "text": content
            }
            chunks.append(chunk)
        text_buffer = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(tqdm(pdf.pages, desc=f"  Parsing {volume_name}")):
                page_num = i + 1
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    # --- NOISE FILTERING ---
                    # 1. Skip Page Numbers (Just digits)
                    if re.match(r'^\d+$', line):
                        continue
                    
                    # 2. Skip Running Headers (Book Title)
                    # Pattern: "LỊCH SỬ VIỆT NAM - TẬP..." or variations
                    if "LỊCH SỬ VIỆT NAM" in line.upper() and ("TẬP" in line.upper() or "CHƯƠNG" not in line.upper()):
                        # Be careful not to skip the REAL chapter title if it mentions the book name (unlikely)
                        # Usually running headers are like "LỊCH SỬ VIỆT NAM - TẬP 10"
                        continue
                        
                    # 3. Skip standalone "CHƯƠNG..." if it's a running header (duplicated)
                    # This is harder to detect, but usually running headers are consistent. 
                    # We will assume regex capture handles real chapters.
                    
                    # --- END FILTERING ---

                    # Heuristic: Check exact patterns and Length
                    is_header = False
                    
                    # Helper to split "Title. Content"
                    def split_run_in_header(full_text, marker_type):
                        # Try to split by first dot or colon
                        # e.g "1. Hoàn cảnh. Năm 1945..." -> Title: "1. Hoàn cảnh", Body: "Năm 1945..."
                        # Pattern: ^(Marker match)(Separator)(Body)
                        # Actually we have match.group(2) which is "Hoàn cảnh. Năm 1945..."
                        
                        # Heuricstic: If text is long (> 80 chars) and contains '.', likely run-in.
                        # If short, likely just title.
                        if len(full_text) > 80 or ('.' in full_text and len(full_text) > 30):
                             # Try split
                             parts = re.split(r'[:\.]\s+', full_text, 1)
                             if len(parts) == 2:
                                 return parts[0].strip(), parts[1].strip()
                        return full_text, ""

                    # 1. Chapter (Always distinct)
                    if len(line) < MAX_HEADER_LENGTH:
                        match_chap = PAT_CHAPTER.match(line)
                        if match_chap:
                            flush_buffer(page_num)
                            current_state['chapter'] = f"CHƯƠNG {match_chap.group(1)}: {match_chap.group(2).strip()}"
                            current_state['lesson'] = ""
                            current_state['roman'] = ""
                            current_state['digit'] = ""
                            current_state['letter'] = ""
                            is_header = True
                    
                    # 2. Lesson (BÀI) (Always distinct)
                    if not is_header and len(line) < MAX_HEADER_LENGTH:
                        match_lesson = PAT_LESSON.match(line)
                        if match_lesson:
                            flush_buffer(page_num)
                            current_state['lesson'] = f"BÀI {match_lesson.group(1)}: {match_lesson.group(2).strip()}"
                            current_state['roman'] = ""
                            current_state['digit'] = ""
                            current_state['letter'] = ""
                            is_header = True

                    # 3. Roman (I.) (Variable, typically distinct)
                    if not is_header and len(line) < MAX_HEADER_LENGTH:
                        match_roman = PAT_ROMAN.match(line)
                        if match_roman:
                            flush_buffer(page_num)
                            title_part, body_part = split_run_in_header(match_roman.group(2).strip(), "ROMAN")
                            
                            current_state['roman'] = f"{match_roman.group(1)}. {title_part}"
                            current_state['digit'] = ""
                            current_state['letter'] = ""
                            is_header = True
                            if body_part:
                                text_buffer.append(body_part)

                    # 4. Digit (1.) (Often run-in)
                    if not is_header: # Remove length check for digit to catch run-in headers
                        match_digit = PAT_DIGIT.match(line)
                        if match_digit:
                            # It's a digit line. Is it a header?
                            # If prev line ended with punctuation, likely a header/start of section.
                            # If prev line looks like running text (no punct), this might be a false positive "1.5 ty dong"
                            # But PDF usually puts headers on new line.
                            
                            # Decide splitting
                            content_matches = match_digit.group(2).strip()
                            title_part, body_part = split_run_in_header(content_matches, "DIGIT")
                            
                            # If body_part exists, definitely a header+content
                            # If no body_part, check length. If < 150, assume Header.
                            if body_part or len(line) < MAX_HEADER_LENGTH:
                                flush_buffer(page_num)
                                current_state['digit'] = f"{match_digit.group(1)}. {title_part}"
                                current_state['letter'] = ""
                                is_header = True
                                if body_part:
                                    text_buffer.append(body_part)

                    # 5. Letter (a)) (Often run-in)
                    if not is_header:
                        match_letter = PAT_LETTER.match(line)
                        if match_letter:
                            content_matches = match_letter.group(2).strip()
                            title_part, body_part = split_run_in_header(content_matches, "LETTER")
                            
                            if body_part or len(line) < MAX_HEADER_LENGTH:
                                flush_buffer(page_num)
                                current_state['letter'] = f"{match_letter.group(1)}) {title_part}"
                                is_header = True
                                if body_part:
                                    text_buffer.append(body_part)
                    
                    if not is_header:
                        text_buffer.append(line)
            
            # End of file flush
            flush_buffer(total_pages)
            
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        
    return chunks

import concurrent.futures

def main():
    if not os.path.exists(PDF_DIR):
        print(f"Directory not found: {PDF_DIR}")
        return

    pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    if not pdf_files:
        print("No PDF files found.")
        return
        
    print(f"Found {len(pdf_files)} PDF files. Starting parallel processing...")
    
    all_chunks = []
    
    # Use ProcessPoolExecutor for CPU-bound PDF parsing
    # Adjust max_workers based on CPU cores (e.g. os.cpu_count())
    max_workers = 8 # User requested fixed 8 threads
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {executor.submit(process_single_pdf, pdf): pdf for pdf in pdf_files}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_file), total=len(pdf_files), desc="Total Progress"):
            pdf_file = future_to_file[future]
            try:
                chunks = future.result()
                all_chunks.extend(chunks)
                # print(f"  -> {os.path.basename(pdf_file)}: {len(chunks)} chunks.")
            except Exception as exc:
                print(f"{os.path.basename(pdf_file)} generated an exception: {exc}")

    print(f"Total chunks extracted: {len(all_chunks)}")
    
    # Save
    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print("Done.")

if __name__ == "__main__":
    main()


import fitz  # PyMuPDF
import json
import time
import os
import re
from googletrans import Translator
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing

# Configuration
PDF_PATH = r"e:\VSCODE_WORKSPACE\VNPT\pdf_data\William Stallings - Computer Organization and Architecture D.pdf"
OUTPUT_PATH = r"e:\VSCODE_WORKSPACE\VNPT\data\stallings_translated.json"
INTERMEDIATE_PATH = r"e:\VSCODE_WORKSPACE\VNPT\data\stallings_extracted_chunks.json"

def get_modal_font_size(pdf_path):
    """Analyze first 50 pages to determine body font size."""
    doc = fitz.open(pdf_path)
    font_sizes = {}
    for page in doc[:50]:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b['type'] == 0:
                for l in b["lines"]:
                    for s in l["spans"]:
                        size = round(s["size"], 1)
                        font_sizes[size] = font_sizes.get(size, 0) + 1
    doc.close()
    if not font_sizes:
        return 12.0
    return max(font_sizes, key=font_sizes.get)

def process_page_range(args):
    """Extract text from a range of pages. Returns list of raw chunks."""
    pdf_path, start_page, end_page, header_threshold = args
    doc = fitz.open(pdf_path)
    
    extracted = []
    current_header = f"Page {start_page} Unknown Section"
    current_text = []
    
    for i in range(start_page, end_page):
        if i >= len(doc): break
        
        try:
            page = doc[i]
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if b['type'] == 0:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            text = s["text"].strip()
                            size = s["size"]
                            
                            if not text or text.isdigit(): continue
                            
                            # Header detection
                            if size > header_threshold and len(text) < 150:
                                if current_text:
                                    full_text = " ".join(current_text)
                                    if len(full_text) > 50:
                                        extracted.append({
                                            "header": current_header,
                                            "content": full_text,
                                            "page": i
                                        })
                                current_header = text
                                current_text = []
                            else:
                                current_text.append(text)
        except Exception as e:
            print(f"Error on page {i}: {e}")
            continue

    if current_text:
        extracted.append({
            "header": current_header,
            "content": " ".join(current_text),
            "page": i
        })
    
    doc.close()
    return extracted

def parallel_translate(chunks, max_workers=10):
    """Translate chunks using ThreadPoolExecutor."""
    translator = Translator()
    translated_data = []
    
    print(f"Starting translation with {max_workers} threads...")
    
    def translate_one(chunk):
        try:
            text = f"{chunk['header']}\n\n{chunk['content']}"
            if len(text) > 5000:
                text = text[:5000] # Truncate for safety for now
            
            # Simple retry logic
            for attempt in range(3):
                try:
                    res = translator.translate(text, src='en', dest='vi')
                    vi_text = res.text
                    break
                except Exception as e:
                    time.sleep(2 * (attempt + 1))
                    if attempt == 2: return None

            if "\n\n" in vi_text:
                head, cont = vi_text.split("\n\n", 1)
            else:
                head, cont = chunk['header'], vi_text
            
            return {
                "source": "William Stallings",
                "original_header": chunk['header'],
                "header": head.strip(),
                "content": cont.strip(),
                "page": chunk['page']
            }
        except:
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(translate_one, c): c for c in chunks}
        
        for future in tqdm(as_completed(futures), total=len(chunks), desc="Translating"):
            result = future.result()
            if result:
                translated_data.append(result)
            
            # Incremental save every 100
            if len(translated_data) % 100 == 0:
                with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                    json.dump(translated_data, f, ensure_ascii=False, indent=2)

    return translated_data

def main():
    # 1. Analyze Font
    modal_size = get_modal_font_size(PDF_PATH)
    print(f"Modal Font Size: {modal_size}")
    header_th = modal_size + 1.0

    # 2. Parallel Extraction
    print("Starting Parallel Extraction...")
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    doc.close()
    
    num_processes = 4
    pages_per_proc = (total_pages + num_processes - 1) // num_processes
    ranges = []
    for i in range(num_processes):
        start = i * pages_per_proc
        end = min((i + 1) * pages_per_proc, total_pages)
        ranges.append((PDF_PATH, start, end, header_th))
    
    all_chunks = []
    with ProcessPoolExecutor(max_workers=num_processes) as pool:
        results = list(tqdm(pool.map(process_page_range, ranges), total=num_processes, desc="Extraction Processes"))
        for res in results:
            all_chunks.extend(res)
            
    print(f"Extracted {len(all_chunks)} chunks.")
    
    # Save Extraction
    with open(INTERMEDIATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2)

    # 3. Parallel Translation
    translated = parallel_translate(all_chunks)
    
    # Final Save
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(translated, f, ensure_ascii=False, indent=2)
    print("Done!")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

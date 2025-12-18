import fitz
import json
import time
import os
import re
from googletrans import Translator
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing

# Configuration
PDF_PATH = r"e:\VSCODE_WORKSPACE\VNPT\pdf_data\Morton.pdf"
OUTPUT_PATH = r"e:\VSCODE_WORKSPACE\VNPT\data\morton_strucutred_translated.json"
INTERMEDIATE_PATH = r"e:\VSCODE_WORKSPACE\VNPT\data\morton_extracted_chunks.json"

# Regex for Structure
RE_PART = re.compile(r"^PART\s+([IVX]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(.*)", re.IGNORECASE)
RE_CHAPTER = re.compile(r"^CHAPTER\s+([0-9]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(.*)", re.IGNORECASE)
# "18 The Deferential-Republican Regime" in footer might not be header.
# Let's detect lines that are ALL CAPS or Title Case and short?
# For now, stick to explicit CHAPTER/PART. If missing, we might get one giant chunk, which is bad.
# Backup: If no regex match for > 10 pages, maybe treat "Page X" as header?

def process_page_range(args):
    pdf_path, start_page, end_page = args
    doc = fitz.open(pdf_path)
    
    extracted = []
    
    current_part = ""
    current_chapter = ""
    current_roman = ""
    
    # We maintain a running buffer of content
    content_buffer = []
    
    # We need to emit a chunk whenever the HIERARCHY changes
    
    def emit_chunk(page_num):
        nonlocal content_buffer
        if not content_buffer: return
        
        text = " ".join(content_buffer).strip()
        if not text: return
        
        # Build hierarchy string
        parts = []
        if current_part: parts.append(current_part)
        if current_chapter: parts.append(current_chapter)
        if current_roman: parts.append(current_roman)
        
        full_title = " > ".join(parts) if parts else f"Page {page_num} Unknown Section"
        
        extracted.append({
            "full_title": full_title,
            "metadata": {
                "part": current_part,
                "chapter": current_chapter,
                "roman": current_roman
            },
            "content": text,
            "page": page_num
        })
        content_buffer = []

    for i in range(start_page, end_page):
        if i >= len(doc): break
        
        try:
            page = doc[i]
            # blocks = page.get_text("dict")["blocks"]
            # Just use text for regex 
            text = page.get_text("text")
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.isdigit(): continue
                
                # Check Regex
                match_part = RE_PART.match(line)
                match_chap = RE_CHAPTER.match(line)
                
                # Update Hierarchy
                if match_part:
                    emit_chunk(i)
                    current_part = line
                    current_chapter = "" # Reset lower hierarchy
                    current_roman = ""
                    continue
                    
                if match_chap:
                    emit_chunk(i)
                    current_chapter = line
                    current_roman = ""
                    continue
                
                # Heuristic for Roman sections? "I. Introduction"
                # Use strict regex
                if re.match(r"^[IVX]+\.\s+[A-Z]", line):
                     emit_chunk(i)
                     current_roman = line
                     continue

                content_buffer.append(line)
                
        except Exception as e:
            print(f"Error on page {i}: {e}")
            continue

    emit_chunk(end_page)
    doc.close()
    return extracted

def parallel_translate(chunks, max_workers=10):
    """Translate chunks using ThreadPoolExecutor."""
    translator = Translator()
    translated_data = []
    
    # Cache for headers to avoid redundant calls
    header_cache = {}

    print(f"Starting translation of {len(chunks)} chunks with {max_workers} threads...")
    
    def translate_text(text):
        if not text or not text.strip(): return ""
        if text in header_cache: return header_cache[text]
        
        try:
            res = translator.translate(text, src='en', dest='vi')
            header_cache[text] = res.text
            return res.text
        except:
            return text

    def translate_one(chunk):
        try:
            # 1. Translate Content
            text_to_trans = chunk['content']
            if len(text_to_trans) > 5000:
                text_to_trans = text_to_trans[:5000] # Truncate

            vi_content = ""
            # Simple retry logic for content
            for attempt in range(3):
                try:
                    if not text_to_trans.strip(): break
                    res = translator.translate(text_to_trans, src='en', dest='vi')
                    vi_content = res.text
                    break
                except Exception as e:
                    time.sleep(2 * (attempt + 1))
            
            final_content = vi_content if vi_content else text_to_trans
            
            # 2. Translate Metadata
            meta = chunk['metadata']
            vi_part = translate_text(meta.get('part', ''))
            vi_chapter = translate_text(meta.get('chapter', ''))
            vi_roman = translate_text(meta.get('roman', ''))
            
            new_metadata = {
                "part": vi_part,
                "chapter": vi_chapter,
                "roman": vi_roman
            }

            # 3. Reconstruct Full Title
            parts = []
            if vi_part: parts.append(vi_part)
            if vi_chapter: parts.append(vi_chapter)
            if vi_roman: parts.append(vi_roman)
            
            # If no hierarchy, keep original full_title logic (e.g. Page X)
            if parts:
                new_full_title = " > ".join(parts)
            else:
                 # Try to translate the fallback title if it's text, else keep
                 new_full_title = translate_text(chunk['full_title'])

            return {
                "full_title": new_full_title,
                "metadata": new_metadata,
                "content": final_content,
                "page": chunk['page']
            }
        except Exception as e:
            print(f"Error translating chunk page {chunk.get('page')}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(translate_one, c): c for c in chunks}
        
        for future in tqdm(as_completed(futures), total=len(chunks), desc="Translating"):
            result = future.result()
            if result:
                translated_data.append(result)
            
    # Sort by page
    translated_data.sort(key=lambda x: x['page'])
    return translated_data

def main():
    print("Starting Morton PDF Extraction...")
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    doc.close()
    
    num_processes = 4
    pages_per_proc = (total_pages + num_processes - 1) // num_processes
    ranges = []
    for i in range(num_processes):
        start = i * pages_per_proc
        end = min((i + 1) * pages_per_proc, total_pages)
        ranges.append((PDF_PATH, start, end))
    
    all_chunks = []
    with ProcessPoolExecutor(max_workers=num_processes) as pool:
        results = list(tqdm(pool.map(process_page_range, ranges), total=num_processes, desc="Extraction Phrases"))
        for res in results:
            all_chunks.extend(res)
            
    print(f"Extracted {len(all_chunks)} chunks. Saving intermediate...")
    
    # Deduplicate chunks? (Page overlap boundaries might cause issues with 'current_header' continuity across processes)
    # The 'current_header' approach in Parallel is flawed because Process 2 doesn't know Process 1's last header.
    # FIX: We should probably run single threaded for extraction OR use a global pass to fix headers.
    # Given PDF size (likely small < 500 pages), single process extraction is fast enough (seconds).
    # Translation handles the heavy lifting.
    
    # Let's switch to SERIAL extraction to ensure hierarchy continuity.
    all_chunks = process_page_range((PDF_PATH, 0, total_pages))
    
    with open(INTERMEDIATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2)

    # Translation
    translated_chunks = parallel_translate(all_chunks)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(translated_chunks, f, ensure_ascii=False, indent=2)
    print(f"Done! Saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

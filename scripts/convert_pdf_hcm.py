import pdfplumber
import json
import re
import os
import sys

PDF_PATH = os.path.join("pdf_data", "Giao-trinh-Tu-tuong-Ho-Chi-Minh.pdf")
OUTPUT_PATH = os.path.join("data", "giao_trinh_hcm_structured.json")

# Regex Patterns
RE_CHAPTER = re.compile(r"^(CHƯƠNG|Chương)\s+([IVX0-9]+)(.*)", re.IGNORECASE)
RE_ROMAN = re.compile(r"^([IVX]+)\.\s+(.*)") # I. Title
RE_NUMBER = re.compile(r"^(\d+)\.\s+(.*)")    # 1. Title
RE_LETTER = re.compile(r"^([a-z])[\)\.]\s+(.*)") # a) Title or a. Title

def parse_pdf():
    if not os.path.exists(PDF_PATH):
        print(f"File not found: {PDF_PATH}")
        return

    print(f"Processing {PDF_PATH}...")
    
    structure = []
    
    current_meta = {
        "chapter": "",
        "roman": "",
        "number": "",
        "letter": ""
    }
    
    current_content = []
    
    # Track the last active header key to append multiline titles
    # Values: 'chapter', 'roman', 'number', 'letter', or None
    last_header_key = None 

    def save_chunk():
        text = "\n".join(current_content).strip()
        if text:
            # Construct a meaningful title path for context
            path_parts = []
            if current_meta['chapter']: path_parts.append(current_meta['chapter'])
            if current_meta['roman']: path_parts.append(current_meta['roman'])
            if current_meta['number']: path_parts.append(current_meta['number'])
            if current_meta['letter']: path_parts.append(current_meta['letter'])
            
            full_title = " > ".join(path_parts)
            
            item = {
                "metadata": current_meta.copy(),
                "full_title": full_title,
                "content": text,
                "source": "Giao-trinh-Tu-tuong-Ho-Chi-Minh.pdf"
            }
            structure.append(item)

    with pdfplumber.open(PDF_PATH) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total Pages: {total_pages}")
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # REORDERED LOGIC: Check explicit headers FIRST
                
                # 1. Chapter
                match_chap = RE_CHAPTER.match(line)
                if match_chap:
                    save_chunk() 
                    current_content = []
                    
                    # Reset lower levels
                    current_meta["chapter"] = line
                    current_meta["roman"] = ""
                    current_meta["number"] = ""
                    current_meta["letter"] = ""
                    
                    last_header_key = "chapter"
                    continue
                
                # 2. Roman (I. )
                match_roman = RE_ROMAN.match(line)
                if match_roman:
                    save_chunk()
                    current_content = []
                    
                    current_meta["roman"] = line
                    current_meta["number"] = ""
                    current_meta["letter"] = ""
                    
                    last_header_key = "roman"
                    continue
                    
                # 3. Number (1. )
                match_num = RE_NUMBER.match(line)
                if match_num:
                    save_chunk()
                    current_content = []
                    
                    current_meta["number"] = line
                    current_meta["letter"] = ""
                    
                    last_header_key = "number"
                    continue
                    
                # 4. Letter (a. or a) )
                match_let = RE_LETTER.match(line)
                if match_let:
                    save_chunk()
                    current_content = []
                    
                    current_meta["letter"] = line
                    
                    last_header_key = "letter"
                    continue

                # HEURISTIC: Check for Multiline Title (Continuation)
                # Matches if NO explicit header found above, but line starts lowercase
                if last_header_key and len(line) > 0 and line[0].islower():
                    # Append to the current metadata field
                    current_meta[last_header_key] += " " + line
                    continue
                
                # Standard content
                current_content.append(line)
                last_header_key = None # We hit content, stop extending headers
                
            if i % 10 == 0:
                print(f"Processed page {i+1}/{total_pages}")

        # Save last chunk
        save_chunk()
        
    print(f"Extracted {len(structure)} chunks.")
    
    # Save to JSON
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    parse_pdf()

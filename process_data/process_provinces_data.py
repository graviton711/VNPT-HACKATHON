
import json
import re
import os

INPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\provinces_wiki.json"
OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\provinces_wiki_chunked.json"

def clean_text_chunk(text):
    # Basic cleaning
    text = text.strip()
    # Remove multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def split_by_sections(content, base_title, province_source):
    chunks = []
    
    # Split by "=== Header ==="
    # Regex to find headers: \n=== Header ===\n
    # Use capturing group to keep the delimiter or just split
    
    # Check if content starts with Intro (before any header)
    # The crawler added "=== Giới thiệu chung ===" so it should be fine.
    
    # Pattern: Matches newline, then =, then text, then =, then newline
    pattern = r'(\n={2,}[^=]+={2,}\n)'
    parts = re.split(pattern, content)
    
    current_header = "Introduction"
    current_text = ""
    
    if len(parts) > 0 and not parts[0].strip().startswith("="):
         # Preamble?
         # Actually our crawler puts "Thông tin về X:\n\n=== Giới thiệu chung ==="
         # So process parts carefully
         pass

    # Reconstruct logic:
    # re.split returns [preamble, header1, text1, header2, text2...]
    
    i = 0
    while i < len(parts):
        part = parts[i]
        
        # Check if this part is a header
        if re.match(r'\n={2,}[^=]+={2,}\n', part):
            header_clean = part.replace('=', '').strip()
            # Capture next part as text
            if i + 1 < len(parts):
                text_content = parts[i+1]
                
                # Further cleaning/splitting if too huge?
                full_text = f"{header_clean}\n{text_content}".strip()
                
                if full_text:
                    chunks.append({
                        "title": f"{base_title} - {header_clean}",
                        "content": clean_text_chunk(full_text),
                        "original_source": "provinces_wiki.json",
                        "province": province_source
                    })
                i += 2
            else:
                i += 1
        else:
            # Maybe preamble text before first header?
            if part.strip():
                 # Don't name it "Introduction" automatically if it's just garbage
                 # But our crawler ensures "=== Giới thiệu chung ===" is first usually.
                 # If "Thông tin về X:" is at start, it might be in part[0]
                 if "Thông tin về" in part:
                     chunks.append({
                        "title": f"{base_title} - Introduction",
                        "content": clean_text_chunk(part),
                        "original_source": "provinces_wiki.json",
                        "province": province_source
                    })
            i += 1
            
    return chunks

def process():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    all_chunks = []
    
    print(f"Processing {len(data)} provinces...")
    
    for doc in data:
        province_name = doc.get("province", "Unknown")
        base_title = doc.get("title", province_name)
        content = doc.get("content", "")
        
        doc_chunks = split_by_sections(content, base_title, province_name)
        all_chunks.extend(doc_chunks)
        
    print(f"Created {len(all_chunks)} chunks.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process()

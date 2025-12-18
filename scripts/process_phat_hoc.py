import pdfplumber
import json
import re
import os

INPUT_PATH = r"pdf_data/PhatHocPhoThong-HTThienHoa.pdf"
OUTPUT_PATH = r"data/phat_hoc_pho_thong.jsonl"

def clean_text(text):
    if not text: return ""
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        s = line.strip()
        if s.isdigit(): continue
        # Removing common headers if needed
        cleaned_lines.append(s)
    return '\n'.join(cleaned_lines)

def process_pdf():
    print(f"Opening {INPUT_PATH}...")
    full_text = ""
    
    with pdfplumber.open(INPUT_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                full_text += clean_text(text) + "\n\n"
            if i % 100 == 0:
                print(f"Extracted {i} pages...")

    print(f"Total Raw Text Length: {len(full_text)} characters.")

    # Chunking Strategy: Split by "BÀI THỨ" (Lesson)
    # The pattern usually looks like: "BÀI THỨ 1:", "BÀI THỨ 2", "BÀI THỨ NHẤT" etc.
    # Or "KHÓA I", "KHÓA II"
    
    # We will try to split by a regex that catches typical headings
    # Pattern: Matches "BÀI THỨ ..." or "KHÓA ..." at start of a line
    
    split_pattern = r'(?=\n(?:BÀI THỨ|KHÓA)\s+)'
    
    raw_chunks = re.split(split_pattern, full_text, flags=re.IGNORECASE)
    
    docs = []
    total_chunks = len(raw_chunks)
    print(f"Splitting found {total_chunks} logical segments.")
    
    for idx, chunk in enumerate(raw_chunks):
        content = chunk.strip()
        if len(content) < 50: continue # Skip noise
        
        # Extract title from first line
        lines = content.split('\n')
        title = lines[0].strip()[:100] # Take first line as title guess
        
        docs.append({
            "source": os.path.basename(INPUT_PATH),
            "title": f"Phật Học Phổ Thông - {title}",
            "author": "Thích Thiện Hoa",
            "text": content,
            "type": "educational_material",
            "chunk_id": idx
        })
    
    print(f"Created {len(docs)} documents.")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        
    print(f"Saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    if not os.path.exists(INPUT_PATH):
        print(f"Please make sure {INPUT_PATH} exists.")
    else:
        process_pdf()

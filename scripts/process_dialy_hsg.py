
import fitz  # PyMuPDF
import json
import re
import os

PDF_PATH = r"e:\VSCODE_WORKSPACE\VNPT\pdf_data\dialy_hsg.pdf"
OUTPUT_PATH = r"e:\VSCODE_WORKSPACE\VNPT\data\dialy_hsg.json"

def clean_text(text):
    # Remove page numbers usually at the bottom
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.isdigit() and len(line) < 4:
            continue
        # Skip generic headers
        if "SÁCH BỒI DƯỠNG" in line.upper() and len(line) < 50:
             continue
        if "ĐỊA LÝ" in line.upper() and len(line) < 20: 
             continue
             
        cleaned_lines.append(line)
        
    text = ' '.join(cleaned_lines)
    # Fix hyphenation
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    # Remove sequences of dots (common in TOCs/Tests)
    text = re.sub(r'\.{2,}', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def semantic_split(text, chunk_size, overlap):
    # 1. Split by Paragraphs
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]
        p_len = len(p)
        
        # Case A: Paragraph allows fitting into current chunk
        if current_length + p_len <= chunk_size:
            current_chunk.append(p)
            current_length += p_len
            i += 1
        else:
            # Case B: Current chunk is full -> Flush it
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                # Reset with overlap
                overlap_buffer = []
                overlap_len = 0
                for old_p in reversed(current_chunk):
                    if overlap_len + len(old_p) < overlap:
                         overlap_buffer.insert(0, old_p)
                         overlap_len += len(old_p)
                    else:
                        break
                current_chunk = overlap_buffer
                current_length = overlap_len
            
            # Case C: Single Paragraph is Huge -> Split by Sentences
            if len(p) > chunk_size:
                sentences = re.split(r'(?<=[.?!])\s+', p)
                temp_chunk = []
                temp_len = 0
                for sent in sentences:
                    if temp_len + len(sent) > chunk_size:
                        chunks.append(" ".join(temp_chunk))
                        last_sent = temp_chunk[-1] if temp_chunk else ""
                        temp_chunk = [last_sent] if len(last_sent) < overlap else []
                        temp_len = len(" ".join(temp_chunk))
                    
                    temp_chunk.append(sent)
                    temp_len += len(sent)
                    
                if temp_chunk:
                    current_chunk.extend(temp_chunk)
                    current_length += temp_len
                i += 1
            else:
                 pass

    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def chunk_text(full_text, chunk_size=800, overlap=200):
    chunks = []
    
    # Expanded Regex for HSG type content
    # Detects: CHUYÊN ĐỀ, CHỦ ĐỀ, PHẦN, BÀI, CHƯƠNG, CÂU
    chapter_pattern = r'(CHUYÊN ĐỀ\s+[\w\d]+|CHỦ ĐỀ\s+[\w\d]+|PHẦN\s+[IVX0-9]+|BÀI\s+[0-9]+|CHƯƠNG\s+[IVX0-9]+|CÂU\s+[0-9]+)'
    
    parts = re.split(chapter_pattern, full_text, flags=re.IGNORECASE)
    
    current_chapter_title = "Địa lý HSG - Tổng quan"
    
    if len(parts) > 0:
        # Preamble
        sub_chunks = semantic_split(parts[0], chunk_size, overlap)
        for s in sub_chunks:
            chunks.append({"title": current_chapter_title, "content": s})

    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        content = parts[i+1] if i+1 < len(parts) else ""
        
        content = clean_text(content)
        if not content: continue
            
        # Refine title
        full_title = f"Địa lý HSG - {header}"
        
        sub_chunks = semantic_split(content, chunk_size, overlap)
        for s in sub_chunks:
             chunks.append({"title": full_title, "content": s})
             
    return chunks

def main():
    print(f"Propcessing {PDF_PATH}...")
    try:
        doc = fitz.open(PDF_PATH)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return

    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
        
    print(f"Extracted {len(full_text)} characters.")
    chunks = chunk_text(full_text)
    print(f"Created {len(chunks)} chunks.")
    
    data_out = []
    for i, c in enumerate(chunks):
        data_out.append({
            "id": f"dialy_hsg_{i}",
            "title": c['title'],
            "content": c['content'],
            "source": "dialy_hsg.pdf"
        })
        
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data_out, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()

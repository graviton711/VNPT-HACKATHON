
import fitz  # PyMuPDF
import json
import re
import os

PDF_PATH = r"e:\VSCODE_WORKSPACE\VNPT\pdf_data\nguyenliketoan.pdf"
OUTPUT_PATH = r"e:\VSCODE_WORKSPACE\VNPT\data\nguyenliketoan.json"

def clean_text(text):
    # Remove page numbers usually at the bottom (simple heuristic: single digits or "Page X")
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip empty lines
        if not line:
            continue
        # Skip obvious page numbers (just digits)
        if line.isdigit() and len(line) < 4:
            continue
        # Skip common headers/footers if detected (heuristic)
        if "Nguyên lý kế toán" in line and len(line) < 30: # Running header
            continue
            
        cleaned_lines.append(line)
        
    text = ' '.join(cleaned_lines)
    # Fix hyphenation
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    # Remove sequences of dots (common in TOCs/Forms)
    text = re.sub(r'\.{2,}', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk_text(full_text, chunk_size=800, overlap=200):
    chunks = []
    
    # 1. Try to split by Chapter Headers first
    # Regex for "Chương 1", "Chương I", "Bài 1", etc.
    # Look for patterns that are likely headers: Uppercase followed by digits/roman numerals
    chapter_pattern = r'(CHƯƠNG\s+[IVX0-9]+|BÀI\s+[0-9]+)'
    
    # Split but keep delimiters
    parts = re.split(chapter_pattern, full_text, flags=re.IGNORECASE)
    
    current_chapter_title = "Nguyên lý kế toán - Tổng quan"
    current_content = ""
    
    # Ensure raw parts are handled
    if len(parts) > 0:
        current_content = parts[0]
        # Process the first preamble chunk
        sub_chunks = semantic_split(current_content, chunk_size, overlap)
        for s in sub_chunks:
            chunks.append({"title": current_chapter_title, "content": s})

    # Iterate through the rest (Delimiter + Content pair)
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        content = parts[i+1] if i+1 < len(parts) else ""
        
        # Clean content
        content = clean_text(content)
        
        if not content:
            continue
            
        # Refine title
        full_title = f"Nguyên lý kế toán - {header} - {content[:50]}..." # Grab first few words as subtitle
        
        # Sub-chunk logic
        sub_chunks = semantic_split(content, chunk_size, overlap)
        
        for s in sub_chunks:
             chunks.append({"title": f"Nguyên lý kế toán - {header}", "content": s})
             
    return chunks

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
                # Reset with overlap: Keep last paragraph(s) if possible
                overlap_buffer = []
                overlap_len = 0
                # Take last few paragraphs that fit into overlap size
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
                # Split huge paragraph by sentences
                sentences = re.split(r'(?<=[.?!])\s+', p)
                
                temp_chunk = []
                temp_len = 0
                
                for sent in sentences:
                    if temp_len + len(sent) > chunk_size:
                        chunks.append(" ".join(temp_chunk))
                        # Simple overlap for sentences
                        last_sent = temp_chunk[-1] if temp_chunk else ""
                        temp_chunk = [last_sent] if len(last_sent) < overlap else []
                        temp_len = len(" ".join(temp_chunk))
                    
                    temp_chunk.append(sent)
                    temp_len += len(sent)
                    
                if temp_chunk:
                    # Treat the remainder of the sentence-split as the start of next paragraph logic
                    current_chunk.extend(temp_chunk)
                    current_length += temp_len
                
                i += 1 # Done with this huge paragraph
            else:
                 # Paragraph fits in empty chunk (or after flush), just continue to next loop
                 # It will be added in Case A next iteration
                 pass

    # Flush final buffer
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
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
    
    # Basic cleaning before chunking
    # full_text = clean_text(full_text) # Done inside chunker for chapter strategy
    
    chunks = chunk_text(full_text)
    print(f"Created {len(chunks)} chunks.")
    
    # Format for RAG
    # Expected format: [{"title": "...", "content": "...", "source": "nguyenliketoan.pdf"}]
    data_out = []
    for i, c in enumerate(chunks):
        data_out.append({
            "id": f"nlkt_{i}",
            "title": c['title'],
            "content": c['content'],
            "source": "nguyenliketoan.pdf"
        })
        
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data_out, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()

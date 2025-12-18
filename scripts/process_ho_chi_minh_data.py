
import json
import re
import os

def clean_text(text):
    """
    Cleans the input text by removing common PDF artifacts.
    """
    if not text:
        return ""
    
    # Remove standalone page numbers (e.g., "  12  ", "\n12\n")
    # Matches lines that contain only digits and whitespace
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove specific headers/footers if found (generic for now)
    # text = re.sub(r'HO CHI MINH IDEOLOGY', '', text, flags=re.IGNORECASE)

    return text.strip()

def chunk_text_by_structure(text, title):
    """
    Chunks text based on structural markers like "CHƯƠNG", "Phần", or Roman Numerals.
    """
    chunks = []
    
    # Strategy: Find all indices of "CHƯƠNG [Number]" or "Phần [Number]"
    # Regex for Chapter/Part headers: 
    # Starts with newline, followed by CHƯƠNG/Phần/Chương, then roman numerals or digits
    # pattern = r'(?:\n|^)\s*(?:CHƯƠNG|Chương|Phần)\s+(?:[IVX]+|\d+).*?(?=\n)'
    
    # More robust pattern to capture the full header line
    pattern = r'((?:\n|^)\s*(?:CHƯƠNG|Chương|Phần)\s+(?:[IVX]+|\d+).*?)(?=\n|$)'
    
    # Split text by pattern, keeping the delimiters (headers)
    parts = re.split(pattern, text)
    
    # parts[0] is usually the preamble/intro before the first chapter
    if parts[0].strip():
        chunks.append({
            "title": f"{title} - Introduction/Preamble",
            "content": parts[0].strip()
        })
    
    # Iterate through the rest: parts[1] is header, parts[2] is content, etc.
    # Because split with capture group returns: [preamble, header1, content1, header2, content2, ...]
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        content = parts[i+1].strip() if i + 1 < len(parts) else ""
        
        full_chunk_text = f"{header}\n\n{content}"
        
        # If chunk is too huge, split by logical paragraphs (simple length check)
        if len(full_chunk_text) > 4000:
             sub_chunks = split_large_chunk(full_chunk_text, f"{title} - {header}")
             chunks.extend(sub_chunks)
        else:
            chunks.append({
                "title": f"{title} - {header}",
                "content": full_chunk_text
            })
            
    return chunks

def split_large_chunk(text, base_title):
    """
    Splits a large chunk into smaller pieces by paragraphs.
    """
    sub_chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""
    part_counter = 1
    
    for para in paragraphs:
        if len(current_chunk) + len(para) < 2000:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                sub_chunks.append({
                    "title": f"{base_title} (Part {part_counter})",
                    "content": current_chunk.strip()
                })
                part_counter += 1
            current_chunk = para + "\n\n"
            
    if current_chunk:
        sub_chunks.append({
            "title": f"{base_title} (Part {part_counter})",
            "content": current_chunk.strip()
        })
        
    return sub_chunks
    

def process_file(input_path, output_path):
    print(f"Processing {input_path}...")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        final_chunks = []
        
        for doc in data:
            original_title = doc.get('title', 'Unknown Title')
            original_content = doc.get('content', '')
            original_metadata = {k:v for k,v in doc.items() if k != 'content'}
            
            # 1. Clean
            cleaned_content = clean_text(original_content)
            
            # 2. Chunk
            chunks = chunk_text_by_structure(cleaned_content, original_title)
            
            # 3. Add metadata back
            for chunk in chunks:
                chunk_obj = original_metadata.copy()
                chunk_obj['title'] = chunk['title']
                chunk_obj['content'] = chunk['content']
                final_chunks.append(chunk_obj)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_chunks, f, ensure_ascii=False, indent=2)
            
        print(f"saved {len(final_chunks)} chunks to {output_path}")

    except Exception as e:
        print(f"Error processing {input_path}: {e}")

if __name__ == "__main__":
    files_to_process = [
        ("data/giao_trinh_tu_tuong_ho_chi_minh.json", "data/giao_trinh_tu_tuong_ho_chi_minh_chunked.json"),
    ]
    
    for input_file, output_file in files_to_process:
        if os.path.exists(input_file):
            process_file(input_file, output_file)
        else:
            print(f"File not found: {input_file}")

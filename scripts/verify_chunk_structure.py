import sys
import os
import re

# --- MOCK CHUNKER (Simplified for strict test) ---
class RecursiveChunker:
    def __init__(self, chunk_size=1200, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text):
        # Extremely simplified splitter for test visualization
        if len(text) <= self.chunk_size: return [text]
        mid = len(text) // 2
        return [text[:mid], text[mid:]]            

# --- COPIED LOGIC FROM indexer.py (To ensure fidelity) ---
def simulate_law_chunking(item):
    chunker = RecursiveChunker()
    all_docs = []
    
    header = f"Tiêu đề: {item.get('title')}\n"
    if item.get('issuance_date'): header += f"Ngày ban hành: {item.get('issuance_date')}\n"
    
    t = item.get('article_title')
    c = item.get('article_content')
    title = item.get('title')
    file_basename = "test_law.json"
    issuance = item.get('issuance_date')
    effective = ""

    full_article = header + t + "\n" + c
    
    # Logic from Indexer
    if len(full_article) > 2000:
        # [ENHANCED] Smart Clause Splitting
        clause_pattern = r'(?:\n|^)(\d+\.\s)'
        parts = re.split(clause_pattern, c)
        
        valid_clauses = []
        if len(parts) > 1:
            start_idx = 1 if not parts[0].strip() else 0
            if start_idx == 0:
                valid_clauses.append({"num": "Intro", "content": parts[0]})
                start_idx = 1
            i = start_idx
            while i < len(parts) - 1:
                num_marker = parts[i]
                content = parts[i+1]
                num_clean = num_marker.strip().replace('.', '')
                valid_clauses.append({"num": num_clean, "content": num_marker + content})
                i += 2
        
        if valid_clauses:
            for cl in valid_clauses:
                cl_text = cl['content']
                cl_num = cl['num']
                
                if len(cl_text) > 1500:
                    sub_sub_chunks = chunker.split_text(cl_text)
                    part_sub = 1
                    for sub_sub in sub_sub_chunks:
                        clean_t = t.strip()
                        if not clean_t.endswith('.'): clean_t += '.'
                        
                        rich_title = f"{header}{clean_t} Khoản {cl_num} (Phần {part_sub})"
                        all_docs.append(f"--- CHUNK (Clause Split) ---\n{rich_title}\n{sub_sub[:100]}...[TRUNCATED]...\n")
                        part_sub += 1
                else:
                    clean_t = t.strip()
                    if not clean_t.endswith('.'): clean_t += '.'
                    rich_title = f"{header}{clean_t} Khoản {cl_num}"
                    all_docs.append(f"--- CHUNK (Clause Full) ---\n{rich_title}\n{cl_text[:100]}...[TRUNCATED]...\n")
        else:
             all_docs.append("FALLBACK SPLIT (No Clauses Found)")
    else:
        all_docs.append(f"--- CHUNK (Full Article) ---\n{full_article[:100]}...\n")
        
    return all_docs

def simulate_history_chunking(item):
    header = ""
    # Header Construction
    title = item.get('full_title') # From convert_history
    if title: header += f"Tiêu đề: {title}\n"
    if item.get('category'): header += f"Danh mục: {item.get('category')}\n"
    
    raw = item.get('text')
    # Simulate simple chunking
    chunk_with_context = header + raw
    return [f"--- CHUNK (History) ---\n{chunk_with_context[:200]}...[TRUNCATED]...\n"]

# --- DATA MOCKS ---

# 1. LAW (Long Article with Clauses)
law_item_long = {
    "title": "Thông tư 17/2021/TT-BGDĐT",
    "issuance_date": "22/06/2021",
    "article_title": "Điều 10. Đội ngũ giảng viên",
    "article_content": """1. Chuẩn chương trình phải quy định yêu cầu tối thiểu... (rất dài) ...
2. Yêu cầu đối với giảng viên chủ trì:
a) Phải có bằng Tiến sĩ...
b) Phải có công bố quốc tế...
(Nội dung khoản 2 rất dài...)
3. Yêu cầu về cơ sở vật chất...""" + ("A" * 3000) # Make it > 2000 chars total
}

# 2. HISTORY
history_item = {
    "full_title": "Tập 1 - Chương I - Bài 2: Nguồn gốc dân tộc",
    "text": "Người Việt cổ đã sinh sống tại vùng Bắc Bộ từ hàng ngàn năm trước...",
    "category": "History"
}

print("=== VERIFICATION REPORT ===\n")

print(">>> CASE 1: LEGAL LONG ARTICLE (Split by Clause)")
docs = simulate_law_chunking(law_item_long)
for d in docs: print(d)

print("\n>>> CASE 2: HISTORY ITEM")
docs = simulate_history_chunking(history_item)
for d in docs: print(d)

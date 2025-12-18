import os
import sys

# Add project root to path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import time
import datetime
import requests
from tqdm import tqdm
from src.api import VNPTClient
from src.vector_store import VectorStore
from src.utils import QuotaTracker, RateLimiter
import re
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed


class RecursiveChunker:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text):
        return self._split_text(text, self.separators)

    def _split_text(self, text, separators):
        if not separators:
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        separator = separators[0]
        next_separators = separators[1:]

        if separator not in text and separator != "":
            return self._split_text(text, next_separators)

        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        final_chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            split_len = len(split) + (len(separator) if separator else 0)
            if current_length + split_len > self.chunk_size:
                if current_chunk:
                    doc = separator.join(current_chunk)
                    if doc.strip(): final_chunks.append(doc)
                    current_chunk = []
                    current_length = 0

            current_chunk.append(split)
            current_length += split_len

        if current_chunk:
            doc = separator.join(current_chunk)
            if doc.strip(): final_chunks.append(doc)
        
        result = []
        for chunk in final_chunks:
            if len(chunk) > self.chunk_size:
                result.extend(self._split_text(chunk, next_separators))
            else:
                result.append(chunk)
        return result

def extract_articles(text):
    articles = []
    law_name = ""
    # Improved Heuristic: Look for lines that are MOSTLY uppercase, starting with LUẬT
    lines = text[:5000].split('\n')
    found_law = False
    captured_name_parts = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        
        # Start Condition: "LUẬT" or "BỘ LUẬT"
        if "LUẬT" in stripped.upper() and not found_law:
            if stripped.isupper() or len([c for c in stripped if c.isupper()]) / len(stripped) > 0.8:
                found_law = True
                captured_name_parts.append(stripped)
                continue
        
        # Continue Condition: Next line is also uppercase
        if found_law:
            if stripped.isupper() or len([c for c in stripped if c.isupper()]) / len(stripped) > 0.8:
                    captured_name_parts.append(stripped)
            else:
                # Check if it's just a number or code e.g. "Số: ..." -> Stop
                if "Số:" in stripped or "Căn cứ" in stripped:
                    break
                # If line is short and looks like part of title, keep it? 
                # Safer to stop if not distinctively uppercase.
                break
    
    if captured_name_parts:
        law_name = " ".join(captured_name_parts)

    # 2. Split Articles
    # Pattern: Newline or Start + "Điều" + whitespace/newline + digits + dot
    split_pattern = r'(?:\n|^)(?=Điều\s*(?:\n\s*)?\d+\.)'
    chunks = re.split(split_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    
    for chunk in chunks:
        chunk = chunk.strip()
        # Verify it starts with Điều X.
        if not re.match(r'^Điều\s*(?:\n\s*)?\d+\.', chunk, re.IGNORECASE):
            continue
            
        # Split Title (Điều X. ABC) from Content
        match_header = re.match(r'^(Điều\s*(?:\n\s*)?\d+\.[^\n]*)(\n.*)?$', chunk, re.DOTALL | re.IGNORECASE)
        if match_header:
            title_part = match_header.group(1).replace('\n', ' ').strip() 
            content_part = match_header.group(2).strip() if match_header.group(2) else ""
            
            articles.append({
                't': title_part,
                'c': content_part
            })
        else:
                # Fallback
                lines = chunk.split('\n', 1)
                t = lines[0].strip()
                c = lines[1].strip() if len(lines) > 1 else ""
                articles.append({'t': t, 'c': c})
        
    return articles, law_name

def parse_file(filepath):
    chunker = RecursiveChunker(chunk_size=1200, chunk_overlap=200)
    all_docs = []
    file_basename = os.path.basename(filepath)
    is_jsonl = filepath.endswith('.jsonl')
    local_items = []
    
    try:
        if is_jsonl:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try: local_items.append(json.loads(line))
                    except: pass
        else:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    if isinstance(data, list): 
                        local_items = []
                        for entry in data:
                            # Check for Standard Format
                            if 'chunks' in entry:
                                source = entry.get('source_file', 'unknown')
                                for ch in entry.get('chunks', []):
                                    ch['url'] = source
                                    local_items.append(ch)
                            
                            # Check for History Format (dang_history.json)
                            elif 'volume_name' in entry and 'pages' in entry:
                                volume = entry.get('volume_name', 'history_doc')
                                for p in entry['pages']:
                                    page_text = "\n".join(p.get('sentences', []))
                                    if not page_text.strip(): continue
                                    local_items.append({
                                        'text': page_text,
                                        'title': volume,
                                        'url': f"{volume}_page_{p.get('page_number')}",
                                        'type': 'history',
                                        'category': 'History'
                                    })
                            # Check for Law Documents (VBPL) which need semantic chunking
                            elif 'content' in entry and ('vbpl' in filepath or 'vbpl' in entry.get('url', '') or 'Luật' in entry.get('title', '') or 'Nghị định' in entry.get('title', '')):
                                # Use semantic extractor
                                extracted_articles, law_name = extract_articles(entry['content'])
                                
                                if extracted_articles:
                                    entry['articles'] = extracted_articles
                                    # Enrich title if Law Name found
                                    if law_name:
                                        original_title = entry.get('title', '')
                                        if law_name not in original_title:
                                            entry['title'] = f"{original_title} - {law_name}" if original_title else law_name
                                    
                                local_items.append(entry)

                            # Check for DVCQG Format (dvc_procedures_raw.json)
                            elif 'PROCEDURE_NAME' in entry:
                                if 'STEPS' in entry or 'REQUIREMENTS' in entry:
                                     # Construct rich text representation
                                    proc_text = f"Tên thủ tục: {entry['PROCEDURE_NAME']}\n"
                                    proc_text += f"Cơ quan thực hiện: {entry.get('IMPLEMENTATION_AGENCY', 'N/A')}\n"
                                    proc_text += f"Lĩnh vực: {entry.get('FIELD_NAME', 'N/A')}\n"
                                    
                                    if entry.get('STEPS'):
                                        proc_text += f"\nTrình tự thực hiện:\n{entry['STEPS']}\n"
                                    
                                    if entry.get('REQUIREMENTS'):
                                        proc_text += f"\nThành phần hồ sơ / Yêu cầu:\n{entry['REQUIREMENTS']}"

                                    local_items.append({
                                        'text': proc_text,
                                        'title': entry['PROCEDURE_NAME'],
                                        'url': f"dvc_{entry.get('PROCEDURE_CODE', 'unknown')}",
                                        'type': 'procedure',
                                        'category': entry.get('FIELD_NAME', 'Administrative'),
                                        'source': 'Dịch vụ công Quốc gia'
                                    })
                                else:
                                    local_items.append({
                                        'text': f"Thủ tục: {entry['PROCEDURE_NAME']}\nCơ quan: {entry.get('IMPLEMENTATION_AGENCY', '')}\nLĩnh vực: {entry.get('FIELD_NAME', '')}",
                                        'title': entry['PROCEDURE_NAME'],
                                        'url': f"dvc_{entry.get('PROCEDURE_CODE', 'unknown')}",
                                        'type': 'procedure',
                                        'category': entry.get('FIELD_NAME', 'Administrative'),
                                        'source': 'Dịch vụ công Quốc gia'
                                    })

                            # Check for Ca Dao (cadao_danca.json) Format
                            elif 'cadao' in entry:
                                # Construct rich text for Ca Dao
                                cadao_text = f"Ca dao: {entry['cadao']}\n"
                                if entry.get('giainghia'):
                                    # join list of explanations
                                    explanations = "\n".join(entry['giainghia']) if isinstance(entry['giainghia'], list) else str(entry['giainghia'])
                                    cadao_text += f"\nGiải nghĩa:\n{explanations}"
                                
                                local_items.append({
                                    'text': cadao_text,
                                    'title': 'Ca dao dân ca Việt Nam', # Generic title or first line
                                    'url': f"cadao_{hash(entry['cadao']) % 1000000}", # Simple synthetic ID
                                    'type': 'folk_literature',
                                    'category': 'Ca dao',
                                    'source': 'Văn học dân gian'
                                })

                            # Check for Thanh Ngu (thanhngu.json) Format
                            elif 'thanhngu' in entry:
                                # Construct rich text for Thanh Ngu
                                thanhngu_text = f"Thành ngữ: {entry['thanhngu']}\n"
                                if entry.get('giaithich'):
                                    explanations = "\n".join(entry['giaithich']) if isinstance(entry['giaithich'], list) else str(entry['giaithich'])
                                    thanhngu_text += f"\nGiải thích:\n{explanations}"
                                
                                local_items.append({
                                    'text': thanhngu_text,
                                    'title': entry['thanhngu'],
                                    'url': f"thanhngu_{hash(entry['thanhngu']) % 1000000}",
                                    'type': 'folk_literature',
                                    'category': 'Thành ngữ',
                                    'source': 'Văn học dân gian'
                                })

                            # Check for Stallings Textbook Format
                            elif 'header' in entry and 'content' in entry and 'page' in entry:
                                # Construct context-rich text
                                header_text = entry['header']
                                content_text = entry['content']
                                page_num = entry['page']
                                
                                full_text = f"{header_text}\n{content_text}"
                                
                                local_items.append({
                                    'text': full_text,
                                    'title': header_text,
                                    'url': f"stallings_page_{page_num}",
                                    'type': 'textbook',
                                    'category': 'Computer Architecture',
                                    'source': 'William Stallings',
                                    'page_number': page_num
                                })

                            # Flatten otherwise?
                            # Check for Merger Format (Data Source: luatvietnam crawler)
                            elif 'merger_desc' in entry:
                                local_items.append({
                                    'text': entry['merger_desc'],
                                    'title': entry.get('source_title', 'Nghị quyết Sắp xếp ĐVHC'),
                                    'url': entry.get('source_doc', 'unknown'),
                                    'province': entry.get('province', ''),
                                    'new_unit': entry.get('new_unit', ''),
                                    'category': 'Sắp xếp ĐVHC' 
                                })

                            # Flatten otherwise?
                            else:
                                local_items.append(entry)
                    elif isinstance(data, dict):
                        local_items = data.get('items', [])
                        if not local_items and 'content' in data: local_items = [data]
                        
                        # Check for dang_history format (volume_name, pages)
                        if 'volume_name' in data and 'pages' in data:
                            # Create items from pages
                            volume = data.get('volume_name', 'history_doc')
                            local_items = []
                            for p in data['pages']:
                                page_text = "\n".join(p.get('sentences', []))
                                local_items.append({
                                    'text': page_text,
                                    'title': volume,
                                    'url': f"{volume}_page_{p.get('page_number')}",
                                    'type': 'history',
                                    'category': 'History'
                                })
            except: pass
        
        # --- PROCESSING ITEMS ---
        for item in local_items:
            # [NEW] Support for Structured HCM Data (Map full_title to title)
            if 'full_title' in item:
                 item['title'] = item['full_title']
            if 'source' in item and 'url' not in item:
                 item['url'] = item['source']

            # PRE-PROCESS for Academic/General Data
            if 'subcategory' in item:
                    item['category'] = item['subcategory']
                    # Construct rich title
                    if 'title' in item:
                        item['title'] = f"[{item['subcategory']}] {item['title']}"

            header = ""
            # Enhanced Title Detection
            title = item.get('title') or item.get('name')
            if not title and 'province' in item:
                title = f"Sáp nhập hành chính {item['province']} (2025)"
            if not title:
                title = item.get('source') or "Unknown Document"
                
            if title: header += f"Tiêu đề: {title}\n"
            if item.get('category') and item['category'] != 'Physics_Science': 
                header += f"Danh mục: {item['category']}\n"
            if item.get('type'): header += f"Loại: {item['type']}\n"
            
            # [NEW] Add Dates to Header (Critical for Legal validity)
            issuance = item.get('issuance_date')
            effective = item.get('effective_date')
            
            # Fallback for Circulars (Thông tư) where metadata is a string "Ban hành:..."
            if not issuance and isinstance(item.get('metadata'), str):
                meta_str = item['metadata']
                # Try extract Ban hanh
                if "Ban hành:" in meta_str:
                    try:
                        parts = meta_str.split("Ban hành:")
                        if len(parts) > 1:
                            date_part = parts[1].strip().split(' ')[0] # Simple extraction
                            issuance = date_part
                    except: pass

            if issuance: header += f"Ngày ban hành: {issuance}\n"
            if effective: header += f"Ngày hiệu lực: {effective}\n"
            
            # 1. Semantic Chunking for Legal Articles
            if 'articles' in item and len(item['articles']) > 0:
                for art in item['articles']:
                    t = art.get('t', '')
                    c = art.get('c', '')
                    # Skip if empty
                    if not t and not c: continue
                    
                    # Construct article text
                    art_text = ""
                    if t: art_text += f"{t}\n"
                    if c: art_text += f"{c}"
                    
                    if not art_text.strip(): continue
                    
                    # Force context on article
                    full_article = header + art_text
                    
                    # If article is HUGE, split it. If small, keep strictly as one.
                    if len(full_article) > 2000:
                        sub_chunks = chunker.split_text(art_text) # Split raw, then add header
                        for sub in sub_chunks:
                            all_docs.append({
                                "text": header + sub,
                                "metadata": {
                                    "source": item.get('url', 'unknown'),
                                    "source_file": file_basename,
                                    "title": title,
                                    "article": t.split(':')[0] if ':' in t else t, # No truncation
                                    "issuance_date": issuance or "",
                                    "effective_date": effective or ""
                                }
                            })
                    else:
                        # Optimal case: 1 Article = 1 Doc
                        all_docs.append({
                            "text": full_article,
                            "metadata": {
                                "source": item.get('url', 'unknown'),
                                "source_file": file_basename,
                                "title": title,
                                "article": t.split(':')[0] if ':' in t else t, # No truncation
                                "issuance_date": issuance or "",
                                "effective_date": effective or ""
                            }
                        })
                continue # Done with this item (processed as articles)

            # 2. Regular Text Chunking
            raw = item.get('text') or item.get('content') or item.get('content_text')
            if not raw or len(raw) < 10: continue

            # Split raw text first
            chunks = chunker.split_text(raw)
            for chunk in chunks:
                # Prepend header to EACH chunk to maintain context
                chunk_with_context = header + chunk
                all_docs.append({
                    "text": chunk_with_context,
                    "metadata": {
                        "source_file": file_basename,
                        "source": item.get('url', 'unknown'),
                        "title": title
                    }
                })

    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        
    return all_docs

class Indexer:
    def __init__(self, data_dir="data"):
        self.client = VNPTClient()
        self.vector_store = VectorStore()
        self.data_dir = data_dir
        self.chunker = RecursiveChunker(chunk_size=800, chunk_overlap=200)
        self.quota_tracker = QuotaTracker()



    def _process_batch(self, batch, batch_idx, rate_limiter, session=None):
        """Helper to process a single batch in a thread."""
        try:
            # Wait for rate limit permission
            rate_limiter.wait_for_token()

            batch_texts = [d['text'] for d in batch]
            batch_metas = [d['metadata'] for d in batch]
            
            headers = self.client._get_headers('embedding')
            endpoint = "https://api.idg.vnpt.vn/data-service/vnptai-hackathon-embedding"
            payload = {
                "model": "vnptai_hackathon_embedding",
                "input": batch_texts,
                "encoding_format": "float"
            }
            
            # Send Request (Use Session if available)
            if session:
                response = session.post(endpoint, headers=headers, json=payload, timeout=60)
            else:
                response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 429:
                print(f"\n[CRITICAL] 429 Too Many Requests (Batch {batch_idx}).")
                return False
                
            response.raise_for_status()
            data = response.json()
            
            # Success
            self.quota_tracker.add_usage(1)
            
            # Sort embeddings by index to match input order
            embeddings_sorted = sorted(data['data'], key=lambda x: x['index'])
            embs = [x['embedding'] for x in embeddings_sorted]
            
            # Return data instead of writing to DB to avoid concurrency issues
            return batch_texts, embs, batch_metas

        except Exception as e:
            print(f"Error batch {batch_idx}: {e}")
            return None

    def build_index(self, limit=None, target_file=None, max_workers=15):
        print(f"[DEBUG] Entered build_index. Data Dir: {self.data_dir}")
        import sys
        sys.stdout.flush()
        
        if not os.path.exists(self.data_dir):
            print(f"Directory {self.data_dir} not found.")
            return

        # print(f"Current Index Size: {self.vector_store.count()} documents.")
        # today_usage = self.quota_tracker.get_usage()
        # print(f"Today's API Usage: {today_usage} requests.")
        print("Starting Indexing Process...")
        sys.stdout.flush()

        # 1. Collect Files
        files_to_index = []
        if target_file:
            full_path = os.path.join(self.data_dir, target_file)
            if os.path.exists(full_path):
                files_to_index.append(full_path)
            else:
                # Try finding it if it was just a name
                found = False
                for root, _, files in os.walk(self.data_dir):
                    if target_file in files:
                        files_to_index.append(os.path.join(root, target_file))
                        found = True
                        break
                if not found:
                    print(f"Target file '{target_file}' not found in {self.data_dir}")
                    return
        else:
            for root, dirs, files in os.walk(self.data_dir):
                for file in files:
                    if file.endswith('.jsonl') or file.endswith('.json'):
                        files_to_index.append(os.path.join(root, file))
            files_to_index.sort()
        
        # Filter files that are already indexed (UNLESS targeted specifically)
        files_to_process = []
        for fp in files_to_index:
             bn = os.path.basename(fp)
             
             # If specific file target, skip check (Force bypass to avoid read crash)
             if target_file:
                 files_to_process.append(fp)
             else:
                 if not self.vector_store.has_file(bn):
                     files_to_process.append(fp)
        
        print(f"Found {len(files_to_index)} files, {len(files_to_process)} need indexing.")
        sys.stdout.flush()
        files_to_process = files_to_process[:limit] if limit else files_to_process
        
        if not files_to_process:
            print("No new files to index.")
            return

        # 2. Parallel Parsing (CPU Bound)
        all_docs = []
        print(f"Parsing {len(files_to_process)} files with {max_workers} processes...")
        
        # [WINDOWS FIX] Use ThreadPoolExecutor to prevent BrokenProcessPool error
        # Parsing is fast enough that Threads are fine, and safer on Windows.
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(parse_file, f): f for f in files_to_process}
            for future in tqdm(as_completed(future_to_file), total=len(files_to_process), desc="Parsing Files"):
                result = future.result()
                if result:
                    all_docs.extend(result)

        print(f"Total chunks prepared: {len(all_docs)}")
        if not all_docs:
            print("No documents generated from files.")
            return

        # 3. Multi-threaded Indexing (IO Bound)
        print(f"Parsed. Now batching {len(all_docs)} docs...")
        sys.stdout.flush()

        BATCH_SIZE = 200 # Target Batch Size
        DB_WRITE_BATCH = 1000 # Buffer DB writes
        LIMIT_PER_MINUTE = 500 # Max allowed by API
        MAX_WORKERS = max_workers
        
        rate_limiter = RateLimiter(LIMIT_PER_MINUTE)
        
        # Initialize Session with Robust Retry Strategy
        from urllib3.util.retry import Retry
        session = requests.Session()
        
        retry_strategy = Retry(
            total=5,
            backoff_factor=1, # Wait 1s, 2s, 4s...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=MAX_WORKERS, 
            pool_maxsize=MAX_WORKERS,
            max_retries=retry_strategy
        )
        session.mount('https://', adapter)
        
        # Adaptive Batching
        batches = []
        current_batch = []
        current_tokens = 0
        MAX_EMBEDDING_TOKENS = 7000
        MAX_BATCH_SIZE = 200
        
        print("Grouping batches adaptively...")
        for doc in all_docs:
            t_est = len(doc['text']) / 2.5
            
            # Flush if limits reached
            if (current_tokens + t_est > MAX_EMBEDDING_TOKENS) or (len(current_batch) >= MAX_BATCH_SIZE):
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            
            current_batch.append(doc)
            current_tokens += t_est
            
        if current_batch:
            batches.append(current_batch)

        print(f"Processing {len(batches)} adaptive batches with {MAX_WORKERS} threads...")
        sys.stdout.flush()
        
        write_buffer_texts = []
        write_buffer_embs = []
        write_buffer_metas = []

        try:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                for i, batch in enumerate(batches):
                    # Pass session to worker
                    futures.append(executor.submit(self._process_batch, batch, i, rate_limiter, session))
                
                # Retrieve results as they complete
                for future in tqdm(as_completed(futures), total=len(batches), desc="Indexing Batches"):
                    try:
                        result = future.result()
                        if result:
                            # Unpack
                            b_texts, b_embs, b_metas = result
                            
                            # Buffer Data
                            write_buffer_texts.extend(b_texts)
                            write_buffer_embs.extend(b_embs)
                            write_buffer_metas.extend(b_metas)
                            
                            # Flush Buffer if full
                            if len(write_buffer_texts) >= DB_WRITE_BATCH:
                                self.vector_store.add_batch(write_buffer_texts, write_buffer_embs, write_buffer_metas)
                                write_buffer_texts = []
                                write_buffer_embs = []
                                write_buffer_metas = []
                                
                        else:
                            print("Batch failed (returned None).")
                    except Exception as ex:
                        print(f"CRITICAL ERROR in future result: {ex}")
                        import traceback
                        traceback.print_exc()
            
            # Flush remaining buffer
            if write_buffer_texts:
                self.vector_store.add_batch(write_buffer_texts, write_buffer_embs, write_buffer_metas)
                
        finally:
            session.close()

        print("Indexing completed.")
        sys.stdout.flush()

    def delete_file(self, filename):
        """Delete all documents associated with a source file."""
        filename = os.path.basename(filename) # Ensure we only use the basename
        print(f"Attempting to delete documents for file: {filename}")
        success = self.vector_store.delete_by_metadata({"source_file": filename})
        if success:
             print(f"Successfully deleted all chunks for '{filename}'.")
             print("IMPORTANT: Please delete 'output/retriever_cache_v2.pkl' to clear BM25 cache if it exists.")
        else:
             print(f"Failed to delete or no documents found for '{filename}'.")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--file", type=str, default=None, help="Specific file to index")
    parser.add_argument("--workers", type=int, default=10, help="Number of threads")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory to index")
    parser.add_argument("--delete", type=str, default=None, help="Delete a file from the index")
    args = parser.parse_args()
    
    print("Initializing Indexer...")
    indexer = Indexer(data_dir=args.data_dir)
    print("Indexer Initialized.")
    
    if args.delete:
        indexer.delete_file(args.delete)
    else:
        print(f"Running build_index with limit={args.limit}, target_file={args.file}, workers={args.workers}")
        try:
            indexer.build_index(limit=args.limit, target_file=args.file, max_workers=args.workers)
        except Exception as e:
            print(f"CRITICAL ERROR in build_index: {e}")
            import traceback
            traceback.print_exc()

import sqlite3
import os
import pickle
from pyvi import ViTokenizer
from tqdm import tqdm
import json
import threading
from concurrent.futures import ProcessPoolExecutor

# Helper function must be top-level for pickling
def tokenize_batch_worker(texts):
    return [ViTokenizer.tokenize(t) for t in texts]

class SQLiteBM25:
    """
    Disk-based BM25 implementation using SQLite FTS5.
    Drastically reduces RAM usage compared to in-memory sparse matrices.
    """
    def __init__(self, db_path="bm25_index.db"):
        self.db_path = db_path
        self.local = threading.local()
        
        # Ensure generic setup (table creation) is done once safely
        self._init_db_schema()

    def _get_conn(self):
        """Get thread-local connection."""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path)
            # Enable WAL mode for better concurrency
            self.local.conn.execute("PRAGMA journal_mode=WAL")
        return self.local.conn

    def _init_db_schema(self):
        """Create tables if not exist (run once)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Create FTS5 virtual table
        # [SCHEMA CHECK] Ensure 'raw_content' exists
        try:
            # Check if column exists by selecting from it (limit 0 to be fast)
            cursor.execute("SELECT raw_content FROM documents LIMIT 0")
        except sqlite3.OperationalError:
            # Column missing (Old Schema) -> Rebuild
            print("Schema mismatch detected (missing raw_content). Rebuilding index...")
            cursor.execute("DROP TABLE IF EXISTS documents")
            
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS documents 
            USING fts5(content, metadata, id UNINDEXED, raw_content UNINDEXED)
        ''')
        conn.commit()
        conn.close()

    # ... (skipping property executor)

    def is_empty(self):
        """Check if index has any documents."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM documents LIMIT 1")
            return cursor.fetchone() is None
        except:
            return True

    def index_documents(self, texts, metadatas, ids):
        """
        Index a batch of documents.
        """
        if not texts: return
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        print(f"Indexing {len(texts)} documents into SQLite...")
        
        # 1. Tokenize
        # We use sequential tokenization here to avoid ProcessPool complexity issues within threads/Safe execution
        # (ViTokenizer is fast enough for increments)
        tokenized_texts = []
        for t in texts:
            tokenized_texts.append(ViTokenizer.tokenize(t))
            
        data_tuples = []
        for i, (doc_id, tokens, meta) in enumerate(zip(ids, tokenized_texts, metadatas)):
            raw_content = texts[i] # Original text
            meta_json = json.dumps(meta, ensure_ascii=False)
            data_tuples.append((tokens, meta_json, doc_id, raw_content))
            
        # 2. Insert Batched
        BATCH_SIZE = 500
        try:
            for i in range(0, len(data_tuples), BATCH_SIZE):
                batch = data_tuples[i:i+BATCH_SIZE]
                cursor.executemany("INSERT INTO documents (content, metadata, id, raw_content) VALUES (?, ?, ?, ?)", batch)
                conn.commit()
        except Exception as e:
            print(f"Index Error: {e}")

        print("Indexing completed.")

    def search(self, query, k=10):
        """
        Search utilizing FTS5 BM25 ranking.
        """
        # Tokenize query exactly like documents
        tokenized_query = ViTokenizer.tokenize(query)
        
        # [FIX] Sanitize query for FTS5
        # 1. Split into tokens
        # 2. Wrap in double quotes to treat special chars (like ?, :, -, *) as literals
        # 3. Escape internal double quotes
        tokens = tokenized_query.split()
        if not tokens:
            return []
            
        safe_tokens = ['"{}"'.format(t.replace('"', '""')) for t in tokens]
        fts_query = " OR ".join(safe_tokens)
        
        # No lock needed for read in WAL mode with thread-local conn
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # FTS5 rank() function orders by BM25 score (by default)
        # [FIX] Select 'raw_content' to preserve formatting (LaTeX, etc.)
        sql = f"""
            SELECT id, metadata, rank, raw_content 
            FROM documents 
            WHERE documents MATCH ? 
            ORDER BY rank 
            LIMIT ?
        """
        
        try:
            cursor.execute(sql, (fts_query, k))
            results = []
            for row in cursor.fetchall():
                doc_id, meta_json, rank, raw_content = row
                results.append({
                    "id": doc_id,
                    "metadata": json.loads(meta_json),
                    "score": rank,
                    "text": raw_content # Return ORIGINAL raw text
                })
            return results
        except Exception as e:
            print(f"Search Error: {e}")
            return []

    def get_existing_ids(self):
        """Return set of all doc IDs currently in FTS index."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM documents")
        # Fetch all as set
        return {row[0] for row in cursor.fetchall()}

    def delete_documents(self, doc_ids):
        """Remove specific docs by ID."""
        if not doc_ids: return
        conn = self._get_conn()
        cursor = conn.cursor()
        print(f"Deleting {len(doc_ids)} obsolete documents from SQLite...")
        
        # Batch delete
        list_ids = list(doc_ids)
        BATCH = 900 # SQLite limit variable number
        for i in range(0, len(list_ids), BATCH):
            batch = list_ids[i:i+BATCH]
            placeholders = ','.join(['?'] * len(batch))
            cursor.execute(f"DELETE FROM documents WHERE id IN ({placeholders})", batch)
        
        conn.commit()
        print("Deletion committed.")

    def close(self):
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=True)
        # Thread locals clean up explicitly if needed, but usually GC'd.
        if hasattr(self.local, 'conn'):
            self.local.conn.close()

# Integration Helper
def migrate_to_sqlite(vector_store):
    print("Migrating In-Memory Data to SQLite...")
    docs_text, docs_meta, docs_ids = vector_store.get_all_documents()
    
    db = SQLiteBM25()
    # Clear old data?
    # db.conn.execute("DELETE FROM documents")
    
    db.index_documents(docs_text, docs_meta, docs_ids)
    return db

from .api import VNPTClient
from .vector_store import VectorStore
import numpy as np
import threading
import os
from tqdm import tqdm
import warnings
# import torch (Moved to lazy load)
from .retriever_sqlite import SQLiteBM25
# from sentence_transformers import CrossEncoder (Moved to lazy load)

from .config import DB_PATH, RERANKER_MODEL, RETRIEVER_K, RETRIEVER_FETCH_K, RERANK_POOL_SIZE, MAX_GPU_WORKERS, USE_RERANKER
from .logger import setup_logger
from tenacity import RetryError
from requests.exceptions import HTTPError

# Suppress "clean_up_tokenization_spaces" FutureWarning from transformers
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers.tokenization_utils_base")
# Suppress "overflowing tokens" logging
import logging
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)

logger = setup_logger(__name__)

class Retriever:
    """
    Implements a Hybrid Retrieval System combining Vector Search (Semantic) and BM25 (Lexical).
    Results are fused using Reciprocal Rank Fusion (RRF) and then refined using a Cross-Encoder Reranker.
    
    Attributes:
        client (VNPTClient): API client for generating query embeddings.
        vector_store (VectorStore): ChromaDB wrapper for dense vector retrieval.
        bm25_backend (SQLiteBM25): SQLite-based FTS5 engine for sparse keyword retrieval.
        reranker (CrossEncoder): HuggingFace Cross-Encoder for precise re-ranking of candidates.
    """

    def __init__(self, check_integrity: bool = False):
        """
        Initializes the Retriever components.

        Args:
            check_integrity (bool): If True, performs a full sync check between VectorStore and BM25 index.
                                    If False, executes a fast start checking only if index is empty.
        """
        self.client = VNPTClient()
        self.vector_store = VectorStore()
        
        # SQLite Database Path
        self.db_path = DB_PATH
        self.bm25_backend = SQLiteBM25(self.db_path)
        
        # Checking Integrity:
        if check_integrity or self._is_index_empty():
            if self._is_index_empty():
                logger.info("BM25 Index empty. Building...")
            else:
                logger.info("Forced Integrity Check...")
            self._build_index()
        else:
            logger.info(f"Skipping Index Check (Fast Start). Loaded BM25 from {self.db_path}")

        # Lazy Init Reranker
        self.reranker = None
        self._model_lock = threading.Lock()
        self._gpu_semaphore = threading.Semaphore(MAX_GPU_WORKERS)
    
    def _ensure_reranker_loaded(self):
        """Lazy loads the CrossEncoder model in a thread-safe manner."""
        if not USE_RERANKER:
            self.reranker = False
            return

        if self.reranker is not None:
             return

        with self._model_lock:
            # Double-check inside lock
            if self.reranker is not None:
                return

            try:
                import torch
                from sentence_transformers import CrossEncoder
                
                logger.info(f"Initializing Reranker ({RERANKER_MODEL} - GPU)...")
                self.reranker = CrossEncoder(
                    RERANKER_MODEL, 
                    max_length=512,
                    device='cuda' if torch.cuda.is_available() else 'cpu'
                )
            except Exception as e:
                logger.error(f"Failed to load Reranker: {e}. Defaulting to RRF only.")
                # Set to False to avoid retrying endlessly
                self.reranker = False

    def _is_index_empty(self) -> bool:
        """Checks if the SQLite FTS index is empty."""
        return self.bm25_backend.is_empty()

    def _build_index(self):
        """
        Synchronizes the BM25 (SQLite) index with the VectorStore (ChromaDB).
        Performs a delta sync: deletes obsolete documents and adds new ones.
        """
        logger.info("Checking Index Integrity (Incremental Sync)...")
        
        # 1. Get snapshot of both systems
        sqlite_ids = self.bm25_backend.get_existing_ids() # Set
        vs_ids = self.vector_store.get_all_ids()          # Set
        
        # 2. Calculate Delas
        missing_ids = vs_ids - sqlite_ids
        obsolete_ids = sqlite_ids - vs_ids
        
        # 3. Handle Deletions
        if obsolete_ids:
            logger.info(f"Found {len(obsolete_ids)} documents removed from VectorStore. Syncing...")
            self.bm25_backend.delete_documents(obsolete_ids)
        
        # 4. Handle Additions
        if missing_ids:
            logger.info(f"Found {len(missing_ids)} new documents to index...")
            
            # Fetch content ONLY for missing items
            # ChromaDB get() allows filtering by IDs
            # [FIX] Batch fetch to avoid "too many SQL variables" (999/32766 limit)
            missing_list = list(missing_ids)
            BATCH_FETCH = 2000 # Reduced to 2000 for RAM safety
            
            for i in tqdm(range(0, len(missing_list), BATCH_FETCH), desc="Fetching & Indexing Deltas"):
                batch_ids = missing_list[i : i + BATCH_FETCH]
                
                try:
                    # Fetch batch content
                    results = self.vector_store.collection.get(ids=batch_ids, include=['documents', 'metadatas'])
                    
                    new_texts = results['documents']
                    new_metas = results['metadatas']
                    new_ids = results['ids']
                    
                    if new_texts:
                        self.bm25_backend.index_documents(new_texts, new_metas, new_ids)
                except Exception as e:
                     logger.error(f"Error indexing delta batch {i}: {e}")
                     # Continue to next batch instead of crashing
        else:
            if not obsolete_ids:
                logger.info("BM25 Index is up to date.")

    def search(self, query: str, k: int = RETRIEVER_K, fetch_k: int = RETRIEVER_FETCH_K) -> list:
        """
        Performs Hybrid Search using Reciprocal Rank Fusion (RRF).
        
        Pipeline:
        1. Vector Search (Semantic) -> Top fetch_k
        2. BM25 Search (Keyword) -> Top fetch_k
        3. RRF Fusion -> Unified Ranking
        4. Cross-Encoder Reranking -> Top k

        Args:
            query (str): The search query.
            k (int): Number of final documents to return.
            fetch_k (int): Number of candidates to fetch from each sub-retriever.

        Returns:
            list: List of document dicts with keys ['id', 'text', 'metadata', 'score', 'rrf_score', 'rerank_score'].
        """
        # Parallelize Vector and BM25 Search
        vector_results = []
        bm25_results = []
        
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        t0 = time.time()
        
        def run_vector():
            try:
                # Embedding is sequential to queries anyway, but putting it here cleans up flow
                t_emb_start = time.time()
                emb_response = self.client.get_embedding(query)
                logger.debug(f"Embedding API took: {time.time()-t_emb_start:.2f}s")
                
                if 'data' in emb_response and isinstance(emb_response['data'], list):
                    query_embedding = emb_response['data'][0]['embedding']
                    t_vec_start = time.time()
                    res = self.vector_store.search(query_embedding, k=fetch_k)
                    logger.debug(f"Vector Search took: {time.time()-t_vec_start:.2f}s")
                    return res
            except RetryError as e:
                # Handle Tenacity Retry Errors (usually API failures)
                cause = e.last_attempt.exception() if e.last_attempt else None
                if isinstance(cause, HTTPError) and cause.response.status_code == 401:
                    logger.error("="*60)
                    logger.error("  FATAL ERROR: API UNAUTHORIZED (401)")
                    logger.error("  Your API Key has expired or is invalid.")
                    logger.error("  Please update 'api_keys/api-keys.json' with a fresh key.")
                    logger.error("="*60)
                    # We do NOT print the traceback here to keep it clean for the user
                else:
                    logger.error(f"[Retriever] Vector Retry Error: {e}")
                    # Only print traceback for unknown errors
                    import traceback
                    logger.debug(f"Traceback: {traceback.format_exc()}")
            except Exception as e:
                import traceback
                logger.error(f"[Retriever] Vector Error: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
            return []

        def run_bm25():
            res_list = []
            try:
                t_bm25_start = time.time()
                # SQLite FTS5 rank is "Smaller is Better".
                # search() returns results ordered by rank ASC (Best first).
                # This is compatible with RRF which uses list position (enumerate).
                raw_bm25 = self.bm25_backend.search(query, k=fetch_k)
                logger.debug(f"BM25 Search took: {time.time()-t_bm25_start:.2f}s")
                
                # Convert to standard format for RRF
                # id, metadata, score
                for item in raw_bm25:
                    res_list.append({
                        "id": item["id"],
                        "metadata": item["metadata"],
                        "score": item["score"],
                        "text": item.get("text", "") # [FIX] Use raw text from DB (Preserves LaTeX)
                    })
            except Exception as e:
                logger.error(f"[Retriever] BM25 Error: {e}")
            return res_list

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_vec = executor.submit(run_vector)
            future_bm25 = executor.submit(run_bm25)
            
            vector_results = future_vec.result()
            bm25_results = future_bm25.result()
            
        logger.debug(f"Total Parallel Search took: {time.time()-t0:.2f}s")

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF_score(d) = sum(1 / (k + rank(d)))
        rrf_k = 60
        merged_scores = {}
        doc_map = {}

        def process_ranked_list(ranked_list):
            for rank, item in enumerate(ranked_list):
                doc_key = item.get('id') or item['text']
                if doc_key not in doc_map:
                    doc_map[doc_key] = item
                if doc_key not in merged_scores:
                    merged_scores[doc_key] = 0.0
                merged_scores[doc_key] += 1.0 / (rrf_k + rank + 1)

        process_ranked_list(vector_results)
        process_ranked_list(bm25_results)

        # Sort by RRF score
        sorted_keys = sorted(merged_scores.keys(), key=lambda x: merged_scores[x], reverse=True)
        
        # 4. Reranking (Cross-Encoder)
        # Take Top N candidates from RRF for reranking (Heavy operation)
        rerank_pool = []
        for key in sorted_keys[:RERANK_POOL_SIZE]: 
            doc = doc_map[key]
            doc['rrf_score'] = merged_scores[key]
            rerank_pool.append(doc)

        if self.reranker is None:
            self._ensure_reranker_loaded()

        if self.reranker and rerank_pool:
            # Prepare pairs for Cross-Encoder: [[query, doc_text], ...]
            pairs = [[query, doc['text']] for doc in rerank_pool]
            try:
                # [GPU SAFETY] Limit concurrent GPU access
                # Network threads can be 50, but GPU threads limited to MAX_GPU_WORKERS
                with self._gpu_semaphore:
                    # Predict scores
                    rerank_scores = self.reranker.predict(pairs)
                
                # Assign new scores
                for i, doc in enumerate(rerank_pool):
                    doc['rerank_score'] = float(rerank_scores[i])
                    
                # Sort by new Cross-Encoder score
                reranked_results = sorted(rerank_pool, key=lambda x: x['rerank_score'], reverse=True)
                
                # Return Top K
                return reranked_results[:k]
                
            except Exception as e:
                logger.error(f"Rerank Error: {e}. Returning RRF results.")
                return rerank_pool[:k]
        
        # Fallback if no reranker
        final_results = []
        for key in sorted_keys[:k]:
            doc = doc_map[key]
            doc['rrf_score'] = merged_scores[key]
            final_results.append(doc)

        return final_results

    def get_request_count(self) -> int:
        """Returns the total number of API requests made by the underlying client."""
        return self.client.get_request_count()


import os
import logging

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DB_PATH = os.path.join(BASE_DIR, "bm25_index.db")

# Models
MODEL_SMALL = 'vnptai_hackathon_small'
MODEL_LARGE = 'vnptai_hackathon_large'
RERANKER_MODEL = 'BAAI/bge-reranker-base'
USE_RERANKER = True

# Solver Settings
MAX_RETRIES = 10000
BATCH_SIZE_SMALL = 10

BATCH_SIZE_LARGE = 20       # Reduced from 30 to 20 for better attention/accuracy
MAX_TOKENS_SMALL = 20000
TARGET_MAX_TOKENS_LARGE = 16000 # Reduced from 19k to 16k to prevent 'Lost in the Middle'
MAX_OUTPUT_TOKENS_SMALL = 10024 # High output for CoT
MAX_OUTPUT_TOKENS_LARGE = 1024
CLASSIFICATION_BATCH_SIZE = 20  # Safe to keep high (simple task)

# Rate Limiting (Public Quota)
RATE_LIMIT_SMALL = 60       # req/hour
RATE_LIMIT_LARGE = 40       # req/hour
RATE_LIMIT_EMBEDDING = 500  # req/minute
RATE_LIMIT_INTERVAL_CHAT = 3600 # 1 hour
RATE_LIMIT_INTERVAL_EMBEDDING = 60 # 1 minute

# Retriever Settings
RETRIEVER_K = 5
RETRIEVER_FETCH_K = 50
RRF_K = 50
RERANK_POOL_SIZE = 20     # Reduced to 10 to speed up Reranking (GPU bound)

# Concurrency & Batching Limits
MAX_WORKERS_RAG = 4    # Reduced to fit Total 8
MAX_WORKERS_INFERENCE = 4  # Reduced to fit Total 8
MAX_WORKERS_CALC = 8     # Sequential pass can use full 8
RETRY_BATCH_TOKENS = 18000  # Max tokens per batch for retry loops

# GPU Safety
MAX_GPU_WORKERS = 3 # Limit concurrent Reranker calls to avoid OOM

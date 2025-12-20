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
# Enable Reranker for High Accuracy (8GB VRAM is ample)
RERANKER_MODEL = 'BAAI/bge-reranker-base'
USE_RERANKER = True

# Solver Settings
MAX_RETRIES = 10000
BATCH_SIZE_SMALL = 1  # Single Shot (Max Accuracy)
BATCH_SIZE_LARGE = 1  # Single Shot (Max Accuracy)
MAX_TOKENS_SMALL = 18000
TARGET_MAX_TOKENS_LARGE = 16000 
MAX_OUTPUT_TOKENS_SMALL = 10024 # Override: Limit small model output in private env
MAX_OUTPUT_TOKENS_LARGE = 1024 # Override: Limit large model output in private env
CLASSIFICATION_BATCH_SIZE = 20

# Rate Limiting
RATE_LIMIT_CALLS = 10000 
RATE_LIMIT_INTERVAL = 60

# Aliases for backward compatibility
RATE_LIMIT_SMALL = RATE_LIMIT_CALLS
RATE_LIMIT_LARGE = RATE_LIMIT_CALLS
RATE_LIMIT_EMBEDDING = RATE_LIMIT_CALLS
RATE_LIMIT_INTERVAL_CHAT = RATE_LIMIT_INTERVAL
RATE_LIMIT_INTERVAL_EMBEDDING = RATE_LIMIT_INTERVAL

# Retriever Settings
RETRIEVER_K = 10   # High Context
RETRIEVER_FETCH_K = 60
RRF_K = 50
RERANK_POOL_SIZE = 20   # Assess more candidates (Better GPU)

# Concurrency & Batching Limits
MAX_WORKERS_RAG = 4       # Reduced to fit Total 8
MAX_WORKERS_INFERENCE = 4 # Reduced to fit Total 8
MAX_WORKERS_CALC = 8      # Sequential pass can use full 8
RETRY_BATCH_TOKENS = 18000 

# GPU Safety (Dynamic Detection)
def _detect_gpu_workers():
    import torch
    try:
        if not torch.cuda.is_available():
            return 2
        
        # Hàm này trả về (free, total) tính bằng bytes
        free_bytes, total_bytes = torch.cuda.mem_get_info(0) 
        free_gb = free_bytes / (1024**3)
        
        logging.info(f"VRAM Free/Total: {free_gb:.2f} / {total_bytes/(1024**3):.2f} GB")
        
        # Logic dựa trên bộ nhớ THỰC TẾ còn trống
        if free_gb < 4:
            return 2 # Rất ít bộ nhớ -> Giảm worker tối đa
        elif free_gb < 6:
            return 4
        else:
            return 8
    except:
        return 4

MAX_GPU_WORKERS = _detect_gpu_workers() 

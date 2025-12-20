import time
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd()))

def check_gpu():
    print("--- 1. Checking GPU ---")
    try:
        import torch
        if torch.cuda.is_available():
            print(f"CUDA Available: YES. Device: {torch.cuda.get_device_name(0)}")
        else:
            print("CUDA Available: NO. (This is a problem for Reranker)")
    except ImportError:
        print("Torch not installed.")
    print()

def check_api_latency():
    print("--- 2. Checking API Latency ---")
    try:
        from src.api import VNPTClient
        client = VNPTClient()
        t0 = time.time()
        # Simple dummy embedding
        client.get_embedding("test query")
        print(f"Embedding API Latency: {time.time() - t0:.4f}s")
    except Exception as e:
        print(f"API Error: {e}")
    print()

def check_retriever_speed():
    print("--- 3. Checking Retriever Speed ---")
    try:
        from src.retriever import Retriever
        print("Initializing Retriever...")
        t_init = time.time()
        retriever = Retriever(check_integrity=False)
        print(f"Retriever Init: {time.time() - t_init:.4f}s")
        
        t_search = time.time()
        # Test BM25 Only
        t0 = time.time()
        print("Testing BM25 Search...")
        bm25_res = retriever.bm25_backend.search("thuế thu nhập", k=20)
        print(f"BM25 Time: {time.time() - t0:.4f}s. Items: {len(bm25_res)}")

        # Test Vector Only (Loop to show Warmup)
        print("Testing Vector Search (3 iterations)...")
        emb = retriever.client.get_embedding("thuế thu nhập")['data'][0]['embedding']
        
        for i in range(3):
            t0 = time.time()
            vec_res = retriever.vector_store.search(emb, k=20)
            print(f"  Iter {i+1}: Vector Time: {time.time() - t0:.4f}s. Items: {len(vec_res)}")
        
        # Test Full
        t0 = time.time()
        print("Testing Full Search...")
        results = retriever.search("Công thức tính thuế thu nhập cá nhân", k=10, fetch_k=20)
        print(f"Full Search Time: {time.time() - t0:.4f}s")
    except Exception as e:
        print(f"Retriever Error: {e}")
    print()

if __name__ == "__main__":
    check_gpu()
    check_api_latency()
    check_retriever_speed()

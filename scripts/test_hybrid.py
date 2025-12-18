import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.retriever import Retriever

def test():
    print("Initializing Hybrid Retriever...")
    retriever = Retriever()
    
    # TEST: Standard Query
    query = "Theo phân loại của Morton Keller trong \"Ba chế độ của Mỹ,\" giai đoạn nào trong số các giai đoạn sau được đặc trưng bởi việc chính phủ trung ương có ít ảnh hưởng đến nền kinh tế và tập trung vào các đảng chính trị và tòa án?"
    for i_run in range(1):
        print(f"\n[RUN {i_run+1}] Query: '{query}'")
        print("-" * 40)
        
        t_start = os.times().elapsed if hasattr(os.times(), 'elapsed') else 0 # Simple check
        import time 
        t_start = time.time()
        
        results = retriever.search(query, k=10)
        
        print(f"Total Search Time: {time.time() - t_start:.4f}s")
        
        if not results:
            print("No results found.")
        
        if i_run == 0:
            print("(First run includes cold start latency: Loading Indices + Models)")
            # Only print details for first run to save space? Or both? Let's print summary for 1st.
        
        for i, res in enumerate(results):
            print(f"[{i+1}] RRF: {res.get('rrf_score'):.4f} | Final: {res.get('rerank_score', 0):.4f}")
            print(f"Content: {res['text'][:1024]}...") # Show more content

if __name__ == "__main__":
    test()

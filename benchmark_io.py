import time
import os

FILE_PATH = "/code/chroma_db/chroma.sqlite3"

def benchmark_read():
    if not os.path.exists(FILE_PATH):
        print("ERROR: File not found.")
        return

    size = os.path.getsize(FILE_PATH)
    print(f"File Size: {size / (1024**3):.2f} GB")
    
    print("Starting Raw Read Benchmark (reading entire file)...")
    start_time = time.time()
    
    with open(FILE_PATH, 'rb') as f:
        bytes_read = 0
        while True:
            # Read in large chunks (100MB) to simulate sequential DB scan
            chunk = f.read(1024 * 1024 * 100) 
            if not chunk:
                break
            bytes_read += len(chunk)
            
    end_time = time.time()
    duration = end_time - start_time
    
    speed_mb_s = (size / (1024**2)) / duration
    
    print(f"\n--- BENCHMARK RESULTS ---")
    print(f"Time Taken: {duration:.2f} seconds")
    print(f"Read Speed: {speed_mb_s:.2f} MB/s")
    
    # Analysis
    # ChromaDB default timeout is usually 30s for connection
    TIMEOUT_THRESHOLD = 30
    
    if duration > TIMEOUT_THRESHOLD:
        print(f"\n[FAIL] Read time ({duration:.2f}s) > Threshold ({TIMEOUT_THRESHOLD}s)")
        print("CONCLUSION: PROVEN I/O BOTTLENECK. disk is too slow to load DB before timeout.")
    else:
        print(f"\n[PASS] Read time ({duration:.2f}s) < Threshold ({TIMEOUT_THRESHOLD}s)")
        print("CONCLUSION: Disk is fast enough. The issue might be SQLite Locking/WAL.")

if __name__ == "__main__":
    benchmark_read()

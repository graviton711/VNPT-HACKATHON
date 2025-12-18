import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
logging.basicConfig(level=logging.INFO)

print("--- Testing GPU Detection Logic ---\n")

try:
    from src.config_private import MAX_GPU_WORKERS, _detect_gpu_workers
    
    print(f"Imported MAX_GPU_WORKERS: {MAX_GPU_WORKERS}")
    
    print("\nRe-running detection:")
    workers = _detect_gpu_workers()
    print(f"Detected Workers: {workers}")
    
except Exception as e:
    print(f"Error: {e}")


import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.indexer import Indexer
import logging

logging.basicConfig(level=logging.INFO)

def main():
    indexer = Indexer()
    
    files = [
        "morton_strucutred_translated.json",
        "ky_thuat_do_luong_structured.json"
    ]
    
    # First, try to remove old entries if they exist (clean slate)
    # The source_file metadata matches the filename
    for fname in files:
        print(f"Cleaning old entries for {fname}...")
        try:
             # This deletes docs where metadata['source_file'] == fname. Not strictly exposed in Indexer class properly?
             # Let's check Indexer.delete_file.
             indexer.delete_file(fname)
        except Exception as e:
            print(f"Delete warning: {e}")
            
    # Index files
    for fname in files:
        print(f"Indexing {fname}...")
        try:
            indexer.build_index(target_file=fname)
        except Exception as e:
            print(f"Error indexing {fname}: {e}")
            
    print("Done indexing.")

if __name__ == "__main__":
    main()

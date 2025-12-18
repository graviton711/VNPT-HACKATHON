import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.retriever import Retriever

def main():
    print("Initializing Retriever with Integrity Check forced...")
    # Setting check_integrity=True forces the retriever to sync BM25 with ChromaDB
    retriever = Retriever(check_integrity=True)
    print("BM25 Index verification and update complete.")

if __name__ == "__main__":
    main()

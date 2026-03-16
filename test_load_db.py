import sys
import os

# Create a mock for posthog to avoid potential import errors if missing
from unittest.mock import MagicMock
sys.modules["posthog"] = MagicMock()
sys.modules["chromadb.telemetry.product.posthog"] = MagicMock()

try:
    import chromadb
    print(f"ChromaDB Version: {chromadb.__version__}")
except ImportError:
    print("ChromaDB not installed!")
    sys.exit(1)

from tenacity import retry, stop_after_attempt, wait_fixed

# Minimal VectorStore Init Logic
DB_PATH = "/code/chroma_db"
COLLECTION_NAME = "vnpt_rag_collection"

print(f"Attempting to load ChromaDB from {DB_PATH}...")

try:
    client = chromadb.PersistentClient(path=DB_PATH)
    print("Client initialized successfully.")
    
    coll = client.get_collection(COLLECTION_NAME)
    print(f"Collection '{COLLECTION_NAME}' found.")
    print(f"Item Count: {coll.count()}")
    print("SUCCESS: Database loaded and readable.")
    
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

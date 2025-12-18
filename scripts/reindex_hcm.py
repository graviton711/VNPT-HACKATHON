import sys
import os
sys.path.append(os.getcwd())
from src.indexer import Indexer

# Create Indexer
indexer = Indexer()

# 1. DELETE OLD FILE
old_file = "giao_trinh_tu_tuong_ho_chi_minh_chunked.json"
print(f"Deleting old data from: {old_file}")
indexer.delete_file(old_file)

# 2. INDEX NEW FILE
new_file = "giao_trinh_hcm_structured.json"
print(f"Indexing new data: {new_file}")

# We use build_index targeting the specific file
# Note: build_index(limit=None, target_file=...)
indexer.build_index(target_file=new_file)

print("Re-indexing complete.")

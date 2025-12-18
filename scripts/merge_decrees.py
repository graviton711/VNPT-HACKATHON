import os
import json
import glob
from concurrent.futures import ThreadPoolExecutor

RAW_DIR = r"e:\VSCODE_WORKSPACE\VNPT\data_raw\luatvietnam_merger"
OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\decrees_corpus.json"

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def main():
    print(f"Merging files from {RAW_DIR}...")
    
    # Get all json files
    files = glob.glob(os.path.join(RAW_DIR, "luatvietnam_*.json"))
    print(f"Found {len(files)} chunks.")
    
    if not files:
        print("No files to merge.")
        return

    all_data = []
    
    # Parallel load for speed
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(load_json, files))
        
    for item in results:
        if item:
            all_data.append(item)
            
    # Save to data directory
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    print(f"Saving merged corpus ({len(all_data)} items) to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
        
    print("Done.")

if __name__ == "__main__":
    main()

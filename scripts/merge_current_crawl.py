
import os
import json
import glob
from tqdm import tqdm

SOURCE_DIR = r"e:\VSCODE_WORKSPACE\VNPT\data_raw\legal_crawl"
OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data_raw\legal_crawl_full.json"

def merge_files():
    if not os.path.exists(SOURCE_DIR):
        print(f"Directory {SOURCE_DIR} does not exist.")
        return

    all_data = []
    files = glob.glob(os.path.join(SOURCE_DIR, "*.json"))
    
    print(f"Found {len(files)} files to merge.")
    
    for fpath in tqdm(files, desc="Merging"):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.append(data)
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            
    print(f"Writing {len(all_data)} records to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
        
    print("Done.")

if __name__ == "__main__":
    merge_files()

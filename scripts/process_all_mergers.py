import os
import json
import re

DATA_DIR = r"e:\VSCODE_WORKSPACE\VNPT\data_raw\luatvietnam_merger"
OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\mergers_2025_processed.json"

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def extract_mergers(content):
    mergers = []
    # Heuristic: "thành [phường/xã/thị trấn] mới [tên]"
    # Pattern: "Sắp xếp ... [Unit A], [Unit B] ... thành [Unit New] có tên gọi là [Name]."
    
    # Split content into paragraphs or sentences
    # Resolutiions usually numbered: "1. Sắp xếp...", "2. Sắp xếp..."
    
    # Regex for numbered items starting with "Sắp xếp"
    # Match "Sắp xếp ... thành ... có tên gọi là ... ."
    pattern = re.compile(r"(\d+\.\s+Sắp xếp\s+.*?thành\s+(?:xã|phường|thị trấn)\s+mới\s+.*?)(?=\d+\.\s+Sắp xếp|$)", re.DOTALL)
    
    matches = pattern.findall(content)
    for m in matches:
        text = clean_text(m)
        
        # Extract Old Units
        # "Sắp xếp ... của [Unit A], [Unit B] ... thành"
        # This is tricky because of "một phần diện tích...".
        # Simplified extraction: extract all capitalized names? No.
        
        # Valid strategy:
        # 1. New Unit Name: "có tên gọi là [phường/xã/thị trấn] X."
        new_unit = ""
        new_match = re.search(r"có tên gọi là\s+(?:phường|xã|thị trấn)?\s+([^.]+)", text, re.IGNORECASE)
        if new_match:
            new_unit = new_match.group(1).strip()
            
        # 2. Old Units
        # Everything before "thành"
        # Look for "phường A", "xã B".
        # Regex: `(?:phường|xã|thị trấn)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯ][a-zàáâãèéêìíòóôõùúăđĩũơư]+(?: [A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯ][a-zàáâãèéêìíòóôõùúăđĩũơư]+)*)`
        # This capitalizes words.
        
        # Better: Just keep the full description description as "details" and the new unit name.
        # For RAG, the full sentence "Sắp xếp xã A và xã B thành xã C" is perfect.
        
        if new_unit:
             mergers.append({
                 "full_text": text,
                 "new_unit": new_unit
             })
             
    return mergers

def run():
    all_data = []
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    
    print(f"Processing {len(files)} files...")
    
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                doc = json.load(f)
                
                title = doc.get("title", "")
                province = ""
                pmatch = re.search(r"của\s+(?:Tỉnh|Thành phố)\s+(.+?)(?:\s+năm|\s+giai đoạn|\s*$)", title, re.IGNORECASE)
                if pmatch:
                    province = pmatch.group(1).strip()
                    province = re.sub(r"năm \d{4}.*", "", province).strip()
                
                content = doc.get("content", "")
                mergers = extract_mergers(content)
                
                # If no specific mergers found (maybe format different), use full content?
                # No, we want structured items.
                
                if not mergers and "sắp xếp" in content.lower():
                     # Fallback: maybe just chunk the content by paragraphs?
                     pass
                
                for m in mergers:
                    all_data.append({
                        "province": province,
                        "source_doc": doc.get("doc_id"),
                        "source_title": title,
                        "merger_desc": m["full_text"],
                        "new_unit": m["new_unit"]
                    })
                    
        except Exception as e:
            print(f"Error {filename}: {e}")
            
    print(f"Extracted {len(all_data)} merger records.")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run()

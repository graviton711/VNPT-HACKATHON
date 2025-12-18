
import json
import os

def process():
    input_path = 'data/mergers_2025_raw.json'
    output_path = 'data/mergers_2025.json'
    
    print(f"Loading {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    rows = raw_data.get('data', {}).get('rows', [])
    col_names = raw_data.get('column_names', {}).get('rows', {}).get('columns', ["Tỉnh/Thành", "Đơn vị mới", "Đơn vị cũ"])
    
    print(f"Columns determined: {col_names}")
    print(f"Processing {len(rows)} rows...")
    
    processed_items = []
    
    for row in rows:
        cols = row['columns']
        if len(cols) < 3:
            continue
            
        province = cols[0].strip()
        new_unit = cols[1].strip()
        old_units = cols[2].strip()
        
        # Skip "Không sáp nhập" if needed, or keep it to say "No change"?
        # The prompt asks for merger data. "Không sáp nhập" might be useful info too.
        # But usually we focus on changes.
        # However, for RAG, knowing something is NOT merging is also valuable.
        
        # Construct a descriptive text
        if "Không sáp nhập" in old_units.lower():
            text = f"Năm 2025, tại tỉnh {province}, đơn vị {new_unit}: {old_units}."
        else:
            text = f"Năm 2025, tại tỉnh {province}, thành lập/sắp xếp đơn vị {new_unit} trên cơ sở sáp nhập/điều chỉnh: {old_units}."
            
        item = {
            "source": "SotaGroup Flourish/Nghị quyết 2025",
            "province": province,
            "new_unit": new_unit,
            "old_units": old_units,
            "text": text
        }
        processed_items.append(item)
        
    print(f"Processed {len(processed_items)} items.")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_items, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    process()

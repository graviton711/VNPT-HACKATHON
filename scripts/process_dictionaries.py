import json
import os
from tqdm import tqdm

INPUT_FILES = {
    "data/tu_dien_sinh_hoc_full.json": "sinh_hoc",
    "data/tu_dien_toan_hoc_full.json": "toan_hoc",
    "data/tu_dien_cong_thuc_vat_ly_full.json": "vat_ly",
    "data/data_hoa_hoc_full.json": "hoa_hoc"
}

OUTPUT_FILE = "data/dictionary_combined.jsonl"

def format_sinh_hoc(item):
    cat = item.get("category", "")
    ten = item.get("ten", {})
    t_vi = ten.get("vi", "")
    t_en = ten.get("en", "")
    data = item.get("data", {})
    
    # Flatten data dict
    data_str = ", ".join([f"{k}: {v}" for k, v in data.items()])
    
    text = f"[Sinh học] {cat}\nTên: {t_vi} ({t_en})\nThông tin chi tiết: {data_str}"
    return text

def format_toan_hoc(item):
    lv = item.get("linh_vuc", "")
    ten = item.get("ten", {})
    t_vi = ten.get("vi", "")
    t_en = ten.get("en", "")
    latex = item.get("cong_thuc_latex", "")
    gt = item.get("giai_thich", {})
    gt_vi = gt.get("vi", "")
    
    text = f"[Toán học - {lv}] {t_vi} ({t_en})\nCông thức LaTeX: {latex}\nGiải thích: {gt_vi}"
    return text

def format_vat_ly(item):
    lv = item.get("linh_vuc", "")
    ten = item.get("ten", {})
    t_vi = ten.get("vi", "")
    t_en = ten.get("en", "")
    ct = item.get("cong_thuc", {})
    latex = ct.get("latex", "")
    vars = ct.get("ky_hieu_cac_bien", "")
    gt = item.get("giai_thich_chi_tiet", {})
    mo_ta = gt.get("mo_ta_them_vi", "")
    
    text = f"[Vật lý - {lv}] {t_vi} ({t_en})\nCông thức: {latex}\nKý hiệu biến: {vars}\nMô tả thêm: {mo_ta}"
    return text

def format_hoa_hoc(item):
    pl = item.get("phan_loai", "")
    ten = item.get("ten", {})
    t_vi = ten.get("vi", "")
    t_en = ten.get("en", "")
    dl = item.get("du_lieu", {})
    dl_str = ", ".join([f"{k}: {v}" for k, v in dl.items()])
    
    text = f"[Hóa học - {pl}] {t_vi} ({t_en})\nDữ liệu: {dl_str}"
    return text

FORMATTERS = {
    "sinh_hoc": format_sinh_hoc,
    "toan_hoc": format_toan_hoc,
    "vat_ly": format_vat_ly,
    "hoa_hoc": format_hoa_hoc
}

def process():
    print(f"Processing dictionaries to {OUTPUT_FILE}...")
    
    all_docs = []
    
    for relative_path, type_key in INPUT_FILES.items():
        abs_path = os.path.abspath(relative_path)
        if not os.path.exists(abs_path):
            print(f"[Warning] File not found: {abs_path}")
            continue
            
        print(f"Reading {type_key}: {relative_path}")
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            formatter = FORMATTERS.get(type_key)
            if not formatter:
                continue
                
            for entry in data:
                try:
                    text_content = formatter(entry)
                    doc = {
                        "text": text_content,
                        "source": f"dictionary_{type_key}",
                        "metadata": {"type": "dictionary", "domain": type_key}
                    }
                    all_docs.append(doc)
                except Exception as e:
                    pass # Skip bad entries
                    
        except Exception as e:
            print(f"Error reading {abs_path}: {e}")

    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for doc in all_docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            
    print(f"Done. Wrote {len(all_docs)} documents.")

if __name__ == "__main__":
    process()

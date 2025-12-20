
import ast
import os

def main():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(BASE_DIR, "data", "inferred_map_result.txt")
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract the dict part
    start = content.find("{")
    end = content.rfind("}") + 1
    dict_str = content[start:end]
    
    # Safely eval? No, manual parse to preserve comments if possible, 
    # but ast.literal_eval is safer.
    # The file format is python-like syntax.
    
    try:
        mapping = ast.literal_eval(dict_str)
    except Exception as e:
        print(f"Error parsing: {e}")
        return

    # MANUAL OVERRIDES (The "User Feedback" Layer)
    # \xe5 (229) -> 'ồ' (Hồ)
    mapping['\xe5'] = 'ồ'
    mapping['å'] = 'ồ' # In case it was parsed as char 'å' (0xE5)
    
    # \xdf (223) -> 'ò' (Hòa) - Solver said 'ó'?
    # Let's check \xdf. Solver said 'Ã³' -> 'ó'.
    # If "Hòa bình" -> "H[o]a binh". 'ò' is better.
    # If "Hóa học" -> "H[o]a hoc". 'ó' is better.
    # "Hòa bình" is extremely common in HCM corpus.
    mapping['\xdf'] = 'ò'
    mapping['ß'] = 'ò'
    mapping['\xe3'] = 'ó' # Standard
    
    # Print as Python code
    print("# Auto-generated TCVN3 Map with Manual Overrides")
    print("TCVN3_MAP = {")
    sorted_map = sorted(mapping.items(), key=lambda x: ord(x[0]))
    for k, v in sorted_map:
        hex_code = hex(ord(k))
        print(f"    {repr(k)}: {repr(v)}, # {ord(k)} {hex_code}")
    print("}")

    # Also fix the replacement logic in `convert_hcm.py`
    # (Just printing for copy-paste)

if __name__ == "__main__":
    main()

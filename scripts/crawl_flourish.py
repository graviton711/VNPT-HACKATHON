
import requests
import re
import json
import os

URL = "https://flo.uri.sh/visualisation/23855697/embed"
OUTPUT_RAW = "data/mergers_2025_raw.json"
OUTPUT_CLEAN = "data/mergers_2025.json"

def crawl():
    print(f"Fetching {URL}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    resp = requests.get(URL, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to fetch content. Status: {resp.status_code}")
        return

    content = resp.text
    
    
    # improved extraction using brace counting
    search_str = '_Flourish_data = '
    start_idx = content.find(search_str)
    
    if start_idx == -1:
        print("Could not find '_Flourish_data = ' in content.")
        # Fallback dump
        with open("debug_flourish.html", "w", encoding="utf-8") as f:
            f.write(content)
        return

    # Move to the start of the JSON object
    json_start = start_idx + len(search_str)
    
    # Find the first '{'
    while json_start < len(content) and content[json_start] != '{':
        json_start += 1
        
    if json_start >= len(content):
        print("Could not find start of JSON object after assignment.")
        return

    # Brace counting
    brace_count = 0
    json_end = json_start
    in_string = False
    escape = False
    
    while json_end < len(content):
        char = content[json_end]
        
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end += 1
                    break
        
        json_end += 1
            
    if brace_count != 0:
        print("Failed to find matching closing brace for JSON object.")
        return

    json_str = content[json_start:json_end]
    
    try:
        data = json.loads(json_str)
        print("Successfully parsed _Flourish_data.")
        
        # EXTRACT COLUMN NAMES
        col_search = '_Flourish_data_column_names = '
        col_start = content.find(col_search)
        columns = None
        if col_start != -1:
            col_json_start = col_start + len(col_search)
            # Find start [ or {
            while col_json_start < len(content) and content[col_json_start] not in ['{', '[']:
                col_json_start += 1
            
            # Simple assumption: it's a JSON object or array, let's use the same counter logic
            if col_json_start < len(content):
                c_brace_count = 0
                c_bracket_count = 0
                c_end = col_json_start
                c_in_string = False
                c_escape = False
                
                while c_end < len(content):
                    char = content[c_end]
                    if c_in_string:
                        if c_escape: c_escape = False
                        elif char == '\\': c_escape = True
                        elif char == '"': c_in_string = False
                    else:
                        if char == '"': c_in_string = True
                        elif char == '{': c_brace_count += 1
                        elif char == '}': c_brace_count -= 1
                        elif char == '[': c_bracket_count += 1
                        elif char == ']': c_bracket_count -= 1
                        
                        if c_brace_count == 0 and c_bracket_count == 0:
                            c_end += 1
                            break
                    c_end += 1
                
                col_str = content[col_json_start:c_end]
                try:
                    columns = json.loads(col_str)
                    print("Successfully parsed _Flourish_data_column_names.")
                except:
                    print("Failed to parse column names JSON.")

        # Save raw combined
        output_data = {
            "data": data,
            "column_names": columns
        }

        with open(OUTPUT_RAW, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"Saved raw data to {OUTPUT_RAW}")
        
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        # Save extraction for debugging
        with open("debug_extracted.json", "w", encoding="utf-8") as f:
            f.write(json_str)

if __name__ == "__main__":
    if not os.path.exists('data'):
        os.makedirs('data')
    crawl()

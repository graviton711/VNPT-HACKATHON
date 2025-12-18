
import json
import csv
import os

def main():
    json_path = r"e:\VSCODE_WORKSPACE\VNPT\public_test\review_material.json"
    csv_path = r"e:\VSCODE_WORKSPACE\VNPT\public_test\review_material.csv"
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not data:
            print("No data found in JSON.")
            return

        headers = ['id', 'answer']
        
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for row in data:
                # Convert list of choices to string for CSV cell
                choices_str = "\n".join(row.get('choices', []))
                
                writer.writerow({
                    'id': row.get('id'),
                    'answer': row.get('answer')
                })
                
        print(f"Successfully converted {len(data)} rows to {csv_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

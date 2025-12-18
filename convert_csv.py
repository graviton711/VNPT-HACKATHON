
import json
import csv
import os

def convert_to_csv(json_path, test_path, csv_path):
    print(f"Loading submission from {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            submission_data = json.load(f)
    except FileNotFoundError:
        print("Submission file not found. ensure predict.py ran successfully.")
        return

    # Create map for quick lookup
    # Handle possible variations in key names (id vs qid)
    sub_map = {}
    for item in submission_data:
        qid = item.get('id') or item.get('qid')
        ans = item.get('answer', 'C')
        if qid:
            sub_map[qid] = ans

    print(f"Loading test data from {test_path}...")
    with open(test_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    print(f"Generating CSV to {csv_path}...")
    
    rows = []
    missing_count = 0
    
    for item in test_data:
        qid = item.get('id') or item.get('qid')
        if not qid: continue
        
        if qid in sub_map:
            answer = sub_map[qid]
        else:
            answer = "Z"
            missing_count += 1
            
        rows.append({"id": qid, "answer": answer})
        
    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "answer"])
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Done. Processed {len(rows)} items.")
    print(f"Missing items defaulted to 'C': {missing_count}")

if __name__ == "__main__":
    # Define paths
    json_file = r"e:\VSCODE_WORKSPACE\VNPT\output\submission.json"
    test_file = r"e:\VSCODE_WORKSPACE\VNPT\public_test\test.json"
    csv_file = r"e:\VSCODE_WORKSPACE\VNPT\output\submission.csv"
    
    convert_to_csv(json_file, test_file, csv_file)

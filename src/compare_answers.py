import json
import re
import os

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_review_material(filepath):
    review_answers = {}
    current_id = None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            # Match ID: --- test_0001 ---
            id_match = re.match(r'^---\s*(test_\d+)\s*---', line)
            if id_match:
                current_id = id_match.group(1)
                continue
                
            # Match Answer: CURRENT ANSWER: A
            ans_match = re.match(r'^CURRENT ANSWER:\s*([A-Z])', line)
            if ans_match and current_id:
                review_answers[current_id] = ans_match.group(1)
                current_id = None 
        return review_answers
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return {}

def main():
    base_dir = r"e:\VSCODE_WORKSPACE\VNPT"
    stem_critical_path = os.path.join(base_dir, "public_test", "stem_critical.json")
    submission_path = os.path.join(base_dir, "output", "submission.json")
    review_material_path = os.path.join(base_dir, "public_test", "review_material.txt")
    output_report_path = os.path.join(base_dir, "output", "comparison_report.txt")

    print("Loading files...")
    
    # 1. Load critical IDs
    try:
        stem_critical = load_json(stem_critical_path)
        # Handle if stem_critical is list of dicts or just list
        if isinstance(stem_critical, list):
            if len(stem_critical) > 0 and isinstance(stem_critical[0], dict):
                 critical_ids = set(item['qid'] for item in stem_critical)
            else:
                 # Assume list of strings if not dicts
                 critical_ids = set(stem_critical)
        else:
            print("Unknown format for stem_critical.json")
            return
            
        print(f"Loaded {len(critical_ids)} critical IDs.")
    except Exception as e:
        print(f"Error loading stem_critical.json: {e}")
        return

    # 2. Load Submission
    try:
        submission = load_json(submission_path)
        submission_map = {item['id']: item['answer'] for item in submission}
        print(f"Loaded {len(submission_map)} submission answers.")
    except Exception as e:
        print(f"Error loading submission.json: {e}")
        return

    # 3. Parse Review Material
    review_answers = parse_review_material(review_material_path)
    print(f"Loaded {len(review_answers)} review answers.")

    # 4. Compare
    print("Comparing answers...")
    
    correct_count = 0
    mismatch_count = 0
    missing_submission_count = 0
    
    report_lines = []
    report_lines.append(f"Comparison Report (All Questions)")
    report_lines.append(f"=================")
    
    # Sort IDs for consistent output
    all_review_ids = sorted(list(review_answers.keys()))
    
    for qid in all_review_ids:
        sub_ans = submission_map.get(qid)
        rev_ans = review_answers.get(qid)
        
        if sub_ans is None:
            report_lines.append(f"[MISSING SUBMISSION] {qid}: No submission answer. Review says: {rev_ans}")
            missing_submission_count += 1
            continue
            
        if sub_ans == rev_ans:
            correct_count += 1
        else:
            mismatch_count += 1
            report_lines.append(f"[MISMATCH] {qid}: Submission='{sub_ans}' vs Review='{rev_ans}'")

    total_checked = correct_count + mismatch_count + missing_submission_count
    accuracy = (correct_count / total_checked * 100) if total_checked > 0 else 0
    
    summary = (
        f"\nSummary:\n"
        f"Total Checked: {total_checked}\n"
        f"Matched (Correct): {correct_count}\n"
        f"Mismatched: {mismatch_count}\n"
        f"Missing in Submission: {missing_submission_count}\n"
        f"Accuracy: {accuracy:.2f}%\n"
    )
    
    report_lines.insert(2, summary)
    
    with open(output_report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
        
    print(summary)
    print(f"Detailed report saved to: {output_report_path}")

if __name__ == "__main__":
    main()

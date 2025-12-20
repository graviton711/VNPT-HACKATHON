import json
import os

def evaluate(submission_path, ground_truth_path):
    print(f"Loading submission: {submission_path}")
    try:
        with open(submission_path, 'r', encoding='utf-8') as f:
            submission = json.load(f)
    except FileNotFoundError:
        print("Submission file not found.")
        return

    print(f"Loading ground truth: {ground_truth_path}")
    try:
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
    except FileNotFoundError:
        print("Ground truth file not found.")
        return

    # Create a map of truth
    truth_map = {item['qid']: item['answer'] for item in ground_truth}
    
    correct = 0
    total = 0
    missing = 0
    
    print("\n--- Discrepancies ---")
    for item in submission:
        qid = item.get('id') or item.get('qid')
        pred = item.get('answer')
        
        if qid in truth_map:
            total += 1
            truth = truth_map[qid]
            if pred == truth:
                correct += 1
            else:
                print(f"Question {qid}: Predicted '{pred}' | Actual '{truth}'")
        else:
            missing += 1
            
    if total == 0:
        print("No matching Question IDs found between files.")
        return

    accuracy = (correct / total) * 100
    print("\n--- Results ---")
    print(f"Total Evaluated: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {total - correct}")
    print(f"Accuracy: {accuracy:.2f}%")
    if missing > 0:
        print(f"Warning: {missing} items in submission were not found in ground truth.")

import sys

if __name__ == "__main__":
    if len(sys.argv) > 2:
        sub_path = sys.argv[1]
        gt_path = sys.argv[2]
        evaluate(sub_path, gt_path)
    else:
        # Defaults for quick testing
        evaluate('output/val_50_submission.json', 'public_test/val_50.json')

import json
import re

def parse_review_material(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex to find test ID and CURRENT ANSWER
    # Pattern: --- test_XXXX --- ... CURRENT ANSWER: X
    pattern = re.compile(r'--- (test_\d+) ---.*?CURRENT ANSWER:\s*([A-Z])', re.DOTALL)
    
    matches = pattern.findall(content)
    return {m[0]: m[1] for m in matches}

def parse_submission(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return {item['id']: item['answer'] for item in data}

def compare_answers(review_answers, submission_answers):
    common_ids = set(review_answers.keys()) & set(submission_answers.keys())
    
    matches = []
    mismatches = []
    
    for test_id in common_ids:
        review_ans = review_answers[test_id]
        sub_ans = submission_answers[test_id]
        
        if review_ans == sub_ans:
            matches.append(test_id)
        else:
            mismatches.append((test_id, review_ans, sub_ans))
            
    return matches, mismatches, common_ids

def main():
    review_path = 'e:/VSCODE_WORKSPACE/VNPT/public_test/review_material.txt'
    submission_path = 'e:/VSCODE_WORKSPACE/VNPT/output/submission.json'
    
    print(f"Reading {review_path}...")
    review_answers = parse_review_material(review_path)
    print(f"Found {len(review_answers)} questions in review_material.")
    
    print(f"Reading {submission_path}...")
    submission_answers = parse_submission(submission_path)
    print(f"Found {len(submission_answers)} questions in submission.")
    
    matches, mismatches, common_ids = compare_answers(review_answers, submission_answers)
    
    print("-" * 30)
    print(f"Total Common Questions: {len(common_ids)}")
    print(f"Matching Answers:       {len(matches)}")
    print(f"Mismatches:             {len(mismatches)}")
    print(f"Match Rate:             {len(matches)/len(common_ids)*100:.2f}%")
    print("-" * 30)
    
    if mismatches:
        print("\nDetails of Mismatches (ID: Review -> Submission):")
        # Sort by ID for easier reading
        mismatches.sort(key=lambda x: x[0])
        for m in mismatches:
            print(f"{m[0]}: {m[1]} -> {m[2]}")
            
    # Also verify if any questions are missing from either side
    missing_in_submission = set(review_answers.keys()) - set(submission_answers.keys())
    missing_in_review = set(submission_answers.keys()) - set(review_answers.keys())
    
    if missing_in_submission:
        print(f"\nMissing in submission ({len(missing_in_submission)}): {sorted(list(missing_in_submission))[:10]}...")
    if missing_in_review:
        print(f"\nMissing in review ({len(missing_in_review)}): {sorted(list(missing_in_review))[:10]}...")

if __name__ == "__main__":
    main()

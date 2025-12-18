
import sys
import os
import argparse
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.batch_solver import BatchSolver

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def load_question_by_id(qid, file_path):
    """Load a specific question from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for item in data:
            # Check for id or qid
            item_id = item.get('id') or item.get('qid')
            if str(item_id) == str(qid):
                return item
        return None
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logging.error(f"Error loading file {file_path}: {e}")
        return None

def test_single_question(qid, file_path):
    # Load Item
    print(f"Loading question {qid} from {file_path}...")
    item = load_question_by_id(qid, file_path)
    
    if not item:
        print(f"Error: Question with ID '{qid}' not found in '{file_path}'.")
        return

    solver = BatchSolver()
    
    print("\n--- Testing Question ---")
    print(f"QID: {item.get('id') or item.get('qid')}")
    print(f"Question: {item['question']}")
    print(f"Choices: {item['choices']}")
    print("-" * 30)

    # 1. Prepare
    print("Preparing item (RAG)...")
    prepared_item = solver.prepare_item(item)
    
    # 2. Process
    print(f"Using Model: vnptai_hackathon_small (Default) or Check routing...")
    
    model_name = 'vnptai_hackathon_small'
    batch = [prepared_item]
    
    print(f"Invoking Model ({model_name})...")
    
    # Simple Loop for Multi-turn (Max 3 turns)
    max_turns = 3
    for user_turn in range(max_turns):
        results, pending = solver._process_single_batch(batch, model_name, retry_count=user_turn)
        
        if pending:
            print(f"--- Turn {user_turn + 1} Result: Tool Triggered (Pending) ---")
            # Update the batch with the modified item (context added)
            batch = pending
            # Print specifically what system added (last line usually)
            print(f"System Added Context: {batch[0]['_formatted_text'].splitlines()[-3:]}")
            continue
        
        if results:
            print(f"--- Final Result (Turn {user_turn + 1}) ---")
            res = results[0]
            print(f"Answer: {res.get('answer')}")
            print(f"Reasoning: {res.get('reasoning')}")
            print(f"Confidence: {res.get('confidence')}")
            if res.get('is_sensitive'):
                print("Flagged as SENSITIVE")
            break
        else:
            print("No result returned (Error).")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test Retrieval & Answer for a single unique question.')
    parser.add_argument('--qid', type=str, required=True, help='The ID of the question to test (e.g., test_001)')
    parser.add_argument('--file', type=str, default='public_test/test.json', help='Path to the JSON test file')
    
    args = parser.parse_args()
    
    test_single_question(args.qid, args.file)

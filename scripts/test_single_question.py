
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.batch_solver import BatchSolver

import logging

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def test_single_question():
    solver = BatchSolver()
    
    item = {
       "qid": "test_0249",
    "question": "Máu di chuyển một chiều trong hệ mạch là do",
    "choices": [
      "sức đẩy của tim, sự đàn hồi của thành động mạch, các van động mạch và tĩnh mạch",
      "sức hút của tim, sự đàn hồi của tĩnh mạch và các van tĩnh mạch",
      "tim co bóp, thành mạch đàn hồi và các van tim",
      "sức đẩy và sức hút của tim, sự đàn hồi của thành mạch và các van"
    ]
    }
    
    print("\n--- Testing Single Question ---")
    print(f"Question: {item['question']}")
    print(f"Choices: {item['choices']}")
    print("-" * 30)

    # 1. Prepare
    print("Preparing item (RAG)...")
    prepared_item = solver.prepare_item(item)
    
    # 2. Process
    print(f"Using Model: vnptai_hackathon_small (Default) or Check routing...")
    
    # Check if it was routed to Large (Context) - in this case it likely wont unless RAG adds context
    use_large = prepared_item.get('use_large_model', False)
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
    test_single_question()


import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# MOCK CLASS
class MockVNPTClient:
    def __init__(self, key_file_path='api_keys/api-keys.json'):
        self.request_count = 0
        self.keys = {} 

    def get_embedding(self, text):
        return {"data": [{"embedding": [0.1] * 768}]}

    def chat_completion(self, messages, model='vnptai_hackathon_small', **kwargs):
        # Infer QID from the prompt to make it look realistic
        try:
            prompt = messages[0]['content']
            import re
            match = re.search(r"<question id='(.*?)'>", prompt)
            qid = match.group(1) if match else "unknown_qid"
        except:
            qid = "mock_qid"

        return {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_mock_123",
                    "type": "function",
                    "function": {
                        "name": "submit_batch_results",
                        "arguments": json.dumps({
                            "answers": [
                                {
                                    "id": qid, 
                                    "answer": "A", 
                                    "confidence": 99, 
                                    "reasoning": "This is a MOCK API response. Logic check passed.",
                                    "is_sensitive": False
                                }
                            ]
                        })
                    }
                }
            ]
        }

# PATCHING
# We must patch where it is IMPORTED and USED.
# src.batch_solver imports VNPTClient from src.api

if __name__ == "__main__":
    with patch('src.batch_solver.VNPTClient', side_effect=MockVNPTClient):
        with patch('src.retriever.VNPTClient', side_effect=MockVNPTClient): # Patch retriever too
             # Import original test script logic INSIDE the patch context
            from scripts.test_single_question import test_single_question
            
            print(">>> RUNNING WITH MOCK API (PATCHED) <<<")
            test_single_question('test_0001', 'public_test/test_small.json')

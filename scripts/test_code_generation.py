import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api import VNPTClient
from src.config import MODEL_LARGE
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_code_generation():
    client = VNPTClient()
    
    prompt = "Viết code python tính a+b"
    
    print(f"Testing Model: {MODEL_LARGE}")
    print(f"Prompt: {prompt}\n")
    print("-" * 60)
    
    messages = [
        {"role": "system", "content": "You are a helpful expert Python programmer."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = client.chat_completion(
            messages=messages,
            model=MODEL_LARGE,
            temperature=0.5,
            max_tokens=4096
        )
        
        # VNPTClient.chat_completion returns the 'message' dict directly
        message = response
        content = message.get('content', '')
        print("Response Content:")
        print(content)
        print("-" * 60)
        
    except Exception as e:
        logger.error(f"Error during generation: {e}")

if __name__ == "__main__":
    test_code_generation()

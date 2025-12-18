import json
import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from .logger import setup_logger

logger = setup_logger(__name__)

class VNPTClient:
    """
    Client for interacting with the VNPT AI Hackathon API.
    Handles authentication, request construction, and retries.
    """
    def __init__(self, key_file_path='api_keys/api-keys.json'):
        self.keys = self._load_keys(key_file_path)
        self.base_url = "https://api.idg.vnpt.vn/data-service/v1/chat/completions"
        self.embedding_url = "https://api.idg.vnpt.vn/data-service/vnptai-hackathon-embedding"
        self.request_count = 0

    def get_request_count(self):
        return self.request_count

    def _load_keys(self, key_file_path):
        try:
            with open(key_file_path, 'r') as f:
                data = json.load(f)
            
            keys = {}
            for item in data:
                name = item.get('llmApiName')
                if name == 'LLM small':
                    keys['small'] = item
                elif name == 'LLM large':
                    keys['large'] = item
                elif name == 'LLM embedings':
                    keys['embedding'] = item
            return keys
        except Exception as e:
            logger.error(f"Error loading keys: {e}")
            return {}

    def _get_headers(self, key_type):
        key_data = self.keys.get(key_type)
        if not key_data:
            raise ValueError(f"Key for {key_type} not found")
        
        return {
            'Authorization': key_data['authorization'],
            'Token-id': key_data['tokenId'],
            'Token-key': key_data['tokenKey'],
            'Content-Type': 'application/json'
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def chat_completion(self, messages, model='vnptai_hackathon_small', temperature=0.1, max_tokens=512, top_p=1.0, top_k=50, n=1, response_format=None, logprobs=False, tools=None, tool_choice=None, seed=None):
        self.request_count += 1
        if 'small' in model:
            key_type = 'small'
            endpoint = f"{self.base_url}/vnptai-hackathon-small"
        elif 'large' in model:
            key_type = 'large'
            endpoint = f"{self.base_url}/vnptai-hackathon-large"
        else:
            raise ValueError("Unknown model")

        headers = self._get_headers(key_type)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "n": n,
            "logprobs": logprobs
        }
        if response_format:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        if seed is not None:
            payload["seed"] = seed

        logger.debug(f"  [API] Sending request to {endpoint} (timeout=100)...")
        response = requests.post(endpoint, headers=headers, json=payload, timeout=100)
        logger.debug(f"  [API] Response received from {endpoint} (status={response.status_code}).")
        response.raise_for_status()
        
        data = response.json()
        if 'choices' not in data:
            logger.error(f"API Error Response: {data}")
            raise ValueError(f"API Error: Missing 'choices'. Response: {data}")

        choice = data['choices'][0]
        message = choice['message']
        
        if logprobs and 'logprobs' in choice:
             message['logprobs'] = choice['logprobs']
             
        return message

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_embedding(self, text):
        self.request_count += 1
        key_type = 'embedding'
        headers = self._get_headers(key_type)
        payload = {
            "model": "vnptai_hackathon_embedding",
            "input": text,
            "encoding_format": "float"
        }

        # print(f"[API] Getting embedding... (Length: {len(text)})") # Debug Log
        try:
            response = requests.post(self.embedding_url, headers=headers, json=payload, timeout=60) # Explicit timeout
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[API Error] Embedding failed: {e}")
            raise



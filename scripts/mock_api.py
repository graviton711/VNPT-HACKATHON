from flask import Flask, request, jsonify
import random
import time

app = Flask(__name__)

# Mock Embeddings (Float list of length 768 or 1024)
@app.route('/vnptai-hackathon-embedding', methods=['POST'])
def embedding():
    data = request.json
    texts = data.get('input', [])
    if isinstance(texts, str): texts = [texts]
    
    print(f"[MOCK] Embedding request for {len(texts)} texts")
    
    # Generate random vector
    mock_data = []
    for i in range(len(texts)):
        mock_data.append({
            "object": "embedding",
            "embedding": [random.random() for _ in range(768)], # Standard size
            "index": i
        })
        
    return jsonify({
        "object": "list",
        "data": mock_data,
        "model": "mock-embedding-v1",
        "usage": {"prompt_tokens": 10, "total_tokens": 10}
    })

# Mock Chat Completion
@app.route('/data-service/v1/chat/completions/vnptai-hackathon-small', methods=['POST'])
@app.route('/data-service/v1/chat/completions/vnptai-hackathon-large', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    last_msg = messages[-1]['content'] if messages else ""
    
    print(f"[MOCK] Chat request: {last_msg[:50]}...")
    
    # Simple Mock Answer
    answer = "Đây là câu trả lời kiểm thử từ Mock API. Hệ thống hoạt động tốt."
    
    # Return formatted response
    return jsonify({
        "id": "mock-chat-123",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": data.get('model', 'mock-model'),
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": answer
            },
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
    })

if __name__ == '__main__':
    print("Starting MOCK VNPT API on port 5000...")
    print("Usage: Configure your client to point to http://localhost:5000")
    # Listen on all interfaces
    app.run(host='0.0.0.0', port=5000)

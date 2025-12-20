import http.server
import socketserver
import json
import random
import time
import re

PORT = 5000

class MockHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        # Handle Embedding Request
        if self.path.endswith('/vnptai-hackathon-embedding'):
            self._handle_embedding(data)
        
        # Handle Chat Completion (Small & Large)
        elif '/chat/completions' in self.path:
            self._handle_chat(data)
            
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_embedding(self, data):
        texts = data.get('input', [])
        if isinstance(texts, str): texts = [texts]
        
        print(f"[MOCK] Embedding request for {len(texts)} texts")
        
        mock_data = []
        for i in range(len(texts)):
            mock_data.append({
                "object": "embedding",
                "embedding": [random.random() for _ in range(1024)],
                "index": i
            })
            
        response = {
            "object": "list",
            "data": mock_data,
            "model": "mock-embedding-v1",
            "usage": {"prompt_tokens": 10, "total_tokens": 10}
        }
        self._send_json(response)

    def _handle_chat(self, data):
        messages = data.get('messages', [])
        last_msg = messages[-1]['content'] if messages else ""
        print(f"[MOCK] Chat request: {last_msg[:50]}...")
        
        answer = "MOCK ANSWER: Đây là câu trả lời kiểm thử từ hệ thống giả lập."
        
        response = {
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
        }
        self._send_json(response)

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        # Suppress default logging to keep terminal clean
        return

if __name__ == '__main__':
    print(f"Starting DEPENDENCY-FREE Mock API on port {PORT}...")
    print("Use Ctrl+C to stop.")
    with socketserver.TCPServer(("", PORT), MockHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")

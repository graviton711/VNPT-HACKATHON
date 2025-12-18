
import json
import os
import time
import datetime
import threading

class QuotaTracker:
    def __init__(self, state_file="quota_tracker.json"):
        self.state_file = state_file
        self.load()

    def load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            except:
                self.state = {}
        else:
            self.state = {}

    def get_today_key(self):
        return datetime.datetime.now().strftime("%Y-%m-%d")

    def get_usage(self):
        key = self.get_today_key()
        return self.state.get(key, 0)

    def add_usage(self, count):
        key = self.get_today_key()
        self.state[key] = self.state.get(key, 0) + count
        self.save()

    def save(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f)

class RateLimiter:
    def __init__(self, limit, interval=60):
        self.limit = limit
        self.interval = interval
        self.tokens = limit
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
    def wait_for_token(self):
        while True:
            with self.lock:
                now = time.time()
                if now - self.last_refill >= self.interval:
                    self.tokens = self.limit # Refill
                    self.last_refill = now
                
                if self.tokens > 0:
                    self.tokens -= 1
                    return
                
                # Compute wait time
                wait_time = self.interval - (now - self.last_refill)
            
            # Wait outside lock
            if wait_time > 0:
                time.sleep(wait_time + 0.1)
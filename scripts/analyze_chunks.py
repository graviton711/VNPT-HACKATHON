import json
import os

def analyze(path, name):
    try:
        if not os.path.exists(path):
            print(f"{name}: File not found")
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        lens = [len(c.get('content', '')) for c in data]
        if not lens:
            print(f"{name}: No content")
            return
        print(f"{name}: {len(data)} chunks. Max Length: {max(lens)}, Min Length: {min(lens)}, Avg Length: {sum(lens)/len(lens):.0f}")
    except Exception as e:
        print(f"{name}: Error {e}")

if __name__ == "__main__":
    analyze('data/morton_strucutred_translated.json', 'Morton')
    analyze('data/ky_thuat_do_luong_structured.json', 'KTDL')

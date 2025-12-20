import json

with open('public_test/val.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

subset = data[50:90]

with open('public_test/val_next_40.json', 'w', encoding='utf-8') as f:
    json.dump(subset, f, ensure_ascii=False, indent=2)

print(f"Created public_test/val_next_40.json with {len(subset)} items.")

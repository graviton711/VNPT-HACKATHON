import os

# Define the directory where prompts are stored
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

def _load_prompt(filename: str) -> str:
    """Helper to load prompt content from a file."""
    try:
        path = os.path.join(PROMPTS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error loading prompt from {filename}: {e}")
        return ""

# Domain Specific Prompts matching User Strategy
# 1. NATURAL SCIENCES (Toán, Lý, Hóa, Sinh)
PROMPT_NATURAL_SCIENCE = _load_prompt("natural_science.txt")

# 2. SOCIAL SCIENCES (Sử, Địa, Văn, Chính trị, Xã hội)
PROMPT_SOCIAL_SCIENCE = _load_prompt("social_science.txt")

# 3. ECONOMICS & LAW (Kinh tế, Tài chính, Kế toán, Luật)
PROMPT_ECON_LAW = _load_prompt("econ_law.txt")

# 4. GENERAL / OTHER
PROMPT_GENERAL = _load_prompt("general.txt")

# 5. SENSITIVE / UNSAFE
PROMPT_SENSITIVE = _load_prompt("sensitive.txt")

# 6. READING COMPREHENSION
PROMPT_READING_COMPREHENSION = _load_prompt("reading_comprehension.txt")

# 7. SYSTEMS & STRATEGY (Quản trị, Quy hoạch, Chính sách, ESG)
PROMPT_SYS_STRATEGY = _load_prompt("sys_strategy.txt")

# 8. GEOGRAPHY (Địa lý)
PROMPT_GEOGRAPHY = _load_prompt("geo.txt")

# 9. LITERATURE & ARTS (Văn học, Nghệ thuật)
PROMPT_LITERATURE = _load_prompt("literature.txt")

# 10. RELIGION (Tôn giáo)
PROMPT_RELIGION = _load_prompt("religion.txt")

# Mapping for the Classifier
DOMAIN_MAPPING = {
    "TN": PROMPT_NATURAL_SCIENCE,
    "XH": PROMPT_SOCIAL_SCIENCE,
    "KT": PROMPT_ECON_LAW,
    "ST": PROMPT_SYS_STRATEGY,
    "DL": PROMPT_GEOGRAPHY,
    "NV": PROMPT_LITERATURE,
    "TG": PROMPT_RELIGION,
    "K": PROMPT_GENERAL,
    "S": PROMPT_SENSITIVE,
    "RC": PROMPT_READING_COMPREHENSION
}

# CLASSIFICATION PROMPT
CLASSIFICATION_PROMPT = _load_prompt("classification.txt")

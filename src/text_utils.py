
import re
import json
import logging

# Use basic logging for utils if not fully configured elsewhere
logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> float:
    """
    Estimates the number of tokens in a text string.
    
    Args:
        text (str): The input text.
    
    Returns:
        float: Estimated token count (heuristic: 1 token ~= 2.5 characters for Vietnamese/English mix).
    """
    if not text:
        return 0
    return len(text) / 2.5

def clean_answer(text: str, labels: list) -> str:
    """
    Sanitizes the model's output to ensure it matches one of the valid choice labels.
    
    Args:
        text (str): The raw answer string from the model (e.g., "A.", "Answer: B").
        labels (list): List of valid labels (e.g., ['A', 'B', 'C', 'D']).
        
    Returns:
        str: A single character representing the cleaned answer, or the first label if invalid.
    """
    if not text: return "A" # Default fallback
    
    text = text.strip().upper()
    
    # Exact match
    if len(text) == 1 and text in labels:
        return text
        
    # Search for first valid letter
    match = re.search(r'([A-Z])', text)
    if match:
        found = match.group(1)
        if found in labels:
            return found
            
    return labels[0] if labels else "A"

def extract_answer(response: str, labels: list) -> str:
    """
    Extracts the answer from a free-text response using multiple heuristic patterns.
    
    Args:
        response (str): The full text response from the model.
        labels (list): Valid answer labels.
        
    Returns:
        str: The extracted answer key.
    """
    if not response:
        return labels[0] if labels else "A"
        
    text = response.strip()
    
    # Pattern 1: Explicit labels like "Answer: A" or "Đáp án: A"
    match = re.search(r'(?:Answer|Đáp án|Result):\s*([A-Z])', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
        
    # Pattern 2: Starts with the answer (e.g., "A. This is correct")
    # Limit check to short prefix to avoid false positives in long text
    if len(text) < 5:
        match = re.search(r'^([A-Z])', text)
        if match:
            return match.group(1).upper()
    
    # Pattern 3: Look for answer at the very end of the text
    lines = text.split('\n')
    last_line = lines[-1].strip()
    match = re.search(r'(?:Answer|Đáp án|Result|is)\s*([A-Z])', last_line, re.IGNORECASE)
    if match:
            return match.group(1).upper()
            
    # Pattern 4: Fallback - Check if the text starts with a valid label pattern
    for label in labels:
        if text.startswith(f"{label}.") or text.startswith(f"{label} "):
            return label
            
    # Final Fallback
    return labels[0] if labels else "A"

def parse_partial_json(json_string: str) -> list:
    """
    Attempts to extract valid answer objects from a malformed or truncated JSON string using Regex.
    Useful when the LLM's output is cut off or invalid JSON.
    
    Args:
        json_string (str): The raw JSON-like string.
        
    Returns:
        list: A list of dicts [{"id": "...", "answer": "...", "confidence": 70}, ...]
    """
    valid_answers = []
    
    try:
            # Regex Explanation:
            # "id"\s*:\s*"(?P<id>[^"]+)"  -> Capture ID
            # (?:.(?!\}))*?               -> Non-greedy match of content between keys
            # "answer"\s*:\s*"(?P<answer>[A-J](?:[\.\s])?)" -> Capture Answer (A-J), optional dot/space
            pattern = r'"id"\s*:\s*"(?P<id>[^"]+)"(?:.(?!\}))*?"answer"\s*:\s*"(?P<answer>[A-J](?:[\.\s])?)"'
            
            matches = re.finditer(pattern, json_string, re.DOTALL)
            for match in matches:
                raw_ans = match.group("answer")
                clean_ans = raw_ans.strip().rstrip('.').strip()
                
                valid_answers.append({
                    "id": match.group("id"),
                    "answer": clean_ans,
                    "confidence": 70 # Default confidence for salvaged items
                })
                
    except Exception as e:
        logger.warning(f"Error in partial parsing (answers): {e}")
        
    return valid_answers

def parse_partial_computations(json_string: str) -> list:
    """
    Attempts to extract valid computation objects from malformed JSON.
    
    Args:
        json_string (str): The raw JSON-like string.
        
    Returns:
        list: A list of dicts [{"id": "...", "expression": "..."}, ...]
    """
    valid_comps = []
    try:
        # Pattern: "id": "...", ... "expression": "..."
        pattern = r'"id"\s*:\s*"(?P<id>[^"]+)"(?:.(?!\}))*?"expression"\s*:\s*"(?P<expr>[^"]+)"'
        matches = re.finditer(pattern, json_string, re.DOTALL)
        for match in matches:
            valid_comps.append({
                "id": match.group("id"),
                "expression": match.group("expr")
            })
    except Exception as e:
        logger.warning(f"Error in partial parsing (computations): {e}")
    return valid_comps

def parse_partial_retrievals(json_string: str) -> list:
    """
    Attempts to extract valid retrieval objects from malformed JSON.
    
    Args:
        json_string (str): The raw JSON-like string.
        
    Returns:
        list: A list of dicts [{"id": "...", "keywords": "..."}, ...]
    """
    valid_rets = []
    try:
        # Pattern: "id": "...", ... "keywords": "..."
        pattern = r'"id"\s*:\s*"(?P<id>[^"]+)"(?:.(?!\}))*?"keywords"\s*:\s*"(?P<kw>[^"]+)"'
        matches = re.finditer(pattern, json_string, re.DOTALL)
        for match in matches:
            valid_rets.append({
                "id": match.group("id"),
                "keywords": match.group("kw")
            })
    except Exception as e:
        logger.warning(f"Error in partial parsing (retrievals): {e}")
    return valid_rets


import re
import json
import os

def parse_review_material(input_path, output_path):
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split by the separator "--- test_"
        # We use a regex split to keep the delimiter or just findall?
        # Let's use logic to split by blocks.
        
        # Regex to capture blocks:
        # --- test_0001 ---
        # content
        # CURRENT ANSWER: A
        
        # Matches: --- (test_\d+) ---\n(.*?)\nCURRENT ANSWER: ([A-Z])
        # Use DOTALL to match newlines in content
        pattern = r'--- (test_\d+) ---\n(.*?)\nCURRENT ANSWER: ([A-Z])'
        
        matches = re.findall(pattern, content, re.DOTALL)
        
        results = []
        for test_id, body, answer in matches:
            # Body contains Question and Choices (and sometimes context text)
            # Question usually starts with "Question: "
            # Choices usually start with "A. ", "B. ", etc.
            
            # Simple parsing of body
            # Extract question text
            question_match = re.search(r'Question:\s*(.*?)(?=\n[A-Z]\.|$)', body, re.DOTALL)
            question_text = question_match.group(1).strip() if question_match else ""
            
            if not question_text:
                # Maybe the question is the whole body if no "Question:" label? 
                # But file view shows "Question: " prefix.
                pass
                
            # Extract choices
            choices = []
            choice_pattern = r'\n([A-Z])\.\s*(.*?)(?=\n[A-Z]\.|$|\n$)'
            # This regex for choices is tricky if Choices are multi-line.
            # safer approach: split body by lines, look for lines starting with "A. ", "B. " etc.
            
            lines = body.split('\n')
            
            # Refined Question extraction
            # Find line starting with "Question:"
            q_lines = []
            c_lines = []
            capture_mode = 'text' # text, question, choices
            
            # Actually, simpler: finding the indices of "A. ", "B. " is hard if they appear in text.
            # But usually choices are at the end.
            
            # Let's use the regex for choices which seems standard in this file "A. ", "B. " at start of line?
            # View file shows: 
            # 3: A. Tôi không thể...
            # So yes, start of line.
            
            choice_matches = list(re.finditer(r'\n([A-Z])\.\s+', body))
            
            extracted_choices = []
            if choice_matches:
                # proper text is everything before first choice
                q_text_end = choice_matches[0].start()
                full_q_text = body[:q_text_end].strip()
                if full_q_text.startswith("Question:"):
                    full_q_text = full_q_text[9:].strip()
                
                # Extract choices
                for i, m in enumerate(choice_matches):
                    start = m.end() # content starts after "A. "
                    if i + 1 < len(choice_matches):
                        end = choice_matches[i+1].start()
                    else:
                        end = len(body)
                    
                    choice_content = body[start:end].strip()
                    choice_label = m.group(1) # A, B, C...
                    extracted_choices.append(f"{choice_label}. {choice_content}")
            else:
                # No choices found?
                full_q_text = body.strip()
                if full_q_text.startswith("Question:"):
                    full_q_text = full_q_text[9:].strip()
            
            results.append({
                "id": test_id,
                "question": full_q_text,
                "choices": extracted_choices,
                "answer": answer
            })
            
        # Write to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"Converted {len(results)} items to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parse_review_material(r"e:\VSCODE_WORKSPACE\VNPT\public_test\review_material.txt", r"e:\VSCODE_WORKSPACE\VNPT\public_test\review_material.json")

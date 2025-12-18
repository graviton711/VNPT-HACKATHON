import json
import re

class DataLoader:
    def __init__(self):
        pass

    def load_data(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
            return []

    def extract_context_and_question(self, raw_question):
        # Check for "Đoạn thông tin" pattern
        # Pattern 1: "Đoạn thông tin:\n...Content: ...\nCâu hỏi: ..."
        # Pattern 2: "Đoạn thông tin:\n...\nCâu hỏi: ..."
        
        if "Đoạn thông tin" in raw_question and "Câu hỏi:" in raw_question:
            parts = raw_question.split("Câu hỏi:")
            # Take everything before the last "Câu hỏi:" as context
            context = "Câu hỏi:".join(parts[:-1]).strip()
            question = parts[-1].strip()
            return context, question
        
        return None, raw_question

    def format_choices(self, choices):
        # Handle list of choices
        formatted_choices = []
        labels = []
        
        if isinstance(choices, list):
            for i, choice in enumerate(choices):
                label = chr(65 + i) # A, B, C, ...
                formatted_choices.append(f"{label}. {choice}")
                labels.append(label)
        elif isinstance(choices, dict):
            for key, value in choices.items():
                formatted_choices.append(f"{key}. {value}")
                labels.append(key)
                
        return "\n".join(formatted_choices), labels

    def prepare_prompt_data(self, item):
        raw_question = item.get('question', '')
        raw_choices = item.get('choices', [])
        
        context, question = self.extract_context_and_question(raw_question)
        formatted_choices, labels = self.format_choices(raw_choices)
        
        return {
            'context': context,
            'question': question,
            'formatted_choices': formatted_choices,
            'labels': labels
        }

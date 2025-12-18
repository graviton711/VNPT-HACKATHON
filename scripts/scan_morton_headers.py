import pdfplumber
import re

PDF_PATH = "pdf_data/Morton.pdf"

def scan_headers():
    print(f"Scanning {PDF_PATH}...")
    with pdfplumber.open(PDF_PATH) as pdf:
        # Check first 50 pages
        for i, page in enumerate(pdf.pages[:50]):
            words = page.extract_words(extra_attrs=['size'])
            if not words: continue
            
            # Find max size
            max_size = max(w['size'] for w in words)
            
            # Print lines that are 'large' or start with Chapter
            lines = {} # loose clustering y-tolerance 3
            for w in words:
                y = round(w['top'] / 3) * 3
                if y not in lines: lines[y] = []
                lines[y].append(w)
            
            sorted_ys = sorted(lines.keys())
            for y in sorted_ys:
                line_words = sorted(lines[y], key=lambda x: x['x0'])
                text = " ".join(w['text'] for w in line_words)
                avg_size = sum(w['size'] for w in line_words) / len(line_words)
                
                # Check for "Chapter" or "Part"
                if "CHAPTER" in text.upper() or "PART" in text.upper() or avg_size > 12:
                    print(f"Page {i+1} | Size {avg_size:.1f}: {text}")

if __name__ == "__main__":
    scan_headers()

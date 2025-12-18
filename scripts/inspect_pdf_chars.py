import pdfplumber
import os

pdf_path = "pdf_data/KythuaDoluong/ky-thuat-do-luong_le-quoc-huy_ga_kt-do-luong_lqhuy_c7_cac-chuyen-doi-do-luong-so-cap - [cuuduongthancong.com].pdf"

def inspect_chars():
    with pdfplumber.open(pdf_path) as pdf:
        # Page 10 or 11 seemed to have formulas based on previous `view_file` (chunk around line 2450 was from chapter 7)
        # The view_file output showed "Hình 7.9" likely around page 10-12.
        # Let's check page 10 (0-indexed -> 9, or just loop until we find a formula)
        
        target_page = pdf.pages[10] # Guessing page 11
        chars = target_page.chars
        
        # Look for a sequence that might look like a formula, e.g. "L ="
        # Print char details for a slice
        print(f"Inspecting page {target_page.page_number}...")
        
        count = 0
        for i, char in enumerate(chars):
            # Print a window of characters to spot identifying features
            # We look for 'L', '=', 'W', '2' sequence
            if char['text'] in ['L', '=', 'W', '2', 'u', 's', 'd']:
                 # Print context
                 if count < 50:
                     print(f"Char: '{char['text']}' | Font: {char['fontname']} | Size: {char['size']:.2f} | Y: {char['top']:.2f} | X: {char['x0']:.2f} | Upright: {char['upright']}")
                     count += 1

if __name__ == "__main__":
    inspect_chars()

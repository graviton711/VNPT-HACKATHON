import pdfplumber
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pdf_path = os.path.join(BASE_DIR, "pdf_data", "HCM TOAN TAP", "HO-CHI-MI_636854714264142695.pdf")

with pdfplumber.open(pdf_path) as pdf:
    # Page 1 has "KH¤NG Cã G× Quý H¥N §éC LËP, Tù DO !"
    # Page 16 (approx) has "nhân dân" logic
    # Let's check Page 1 text first
    p1 = pdf.pages[0].extract_text()
    print(f"Page 1 Raw: {p1}")
    print("Page 1 Ordinates:")
    for char in p1:
        if ord(char) > 127:
            print(f"{char}: {ord(char)}", end=" | ")
    print("\n")

    # Scan specific phrases from User feedback to reverse-engineer the map
    # "Hô CHí MINH" (Should be Hồ Chí Minh)
    # "CỗNG SảN" (Should be Cộng Sản)
    # "lội giởi thiệu" (Should be Lời giới thiệu)
    # "THợ BA" (Should be Thứ Ba)
    
    # We will print the first 2000 chars of the file to catching these headers
    print("Dumping first 2000 chars with ordinals:")
    text_page1 = pdf.pages[0].extract_text()
    text_page2 = pdf.pages[1].extract_text()
    full_text = (text_page1 or "") + "\n" + (text_page2 or "")
    
    for char in full_text[:2000]:
        if 32 < ord(char) < 256:
            print(f"'{char}': {ord(char)}", end="  ")
        else:
            print(f"[{ord(char)}]", end=" ")
    print("\nDone.")

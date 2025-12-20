import pdfplumber

pdf_path = r"e:\VSCODE_WORKSPACE\VNPT\pdf_data\HCM TOAN TAP\HO-CHI-MI_636854714264142695.pdf"

with pdfplumber.open(pdf_path) as pdf:
    # Print first 5 pages
    for i in range(10, 20):
        if i >= len(pdf.pages): break
        print(f"--- Page {i+1} ---")
        print(pdf.pages[i].extract_text())
        print("\n")

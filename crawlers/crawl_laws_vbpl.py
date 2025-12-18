import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re
from datetime import datetime
import fitz # PyMuPDF
import io
import tempfile
import urllib3

urllib3.disable_warnings()

# Logic: Crawl "Luật" from VBPL.vn
# Scope: Last 3 years (2025, 2024, 2023)
# Base URL provided by user: https://vbpl.vn/TW/Pages/vanban.aspx?idLoaiVanBan=17&dvid=13

BASE_URL = "https://vbpl.vn/TW/Pages/vanban.aspx?idLoaiVanBan=17&dvid=13&Page={}"
DOMAIN = "https://vbpl.vn"
OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\laws_vbpl_2023_2025.json"
TARGET_YEARS = [2023, 2024, 2025]

def parse_date(date_str):
    try:
        # Expected format: dd/mm/yyyy
        return datetime.strptime(date_str.strip(), "%d/%m/%Y")
    except ValueError:
        return None


def extract_text_from_pdf_url(pdf_url):
    """Downloads PDF and extracts text using PyMuPDF."""
    print(f"    [Fallback] Downloading PDF: {pdf_url}")
    try:
        resp = requests.get(pdf_url, timeout=30, verify=False)
        if resp.status_code != 200:
            print(f"    [Fallback] Failed to download PDF. Status: {resp.status_code}")
            return ""
            
        with fitz.open(stream=resp.content, filetype="pdf") as doc:
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"    [Fallback] Error processing PDF: {e}")
        return ""

def get_detail_content(url, fallback_urls=None):
    """
    Fetches content from 'url' (Toan Van).
    If empty, tries:
      1. 'fallback_urls' passed from list view.
      2. Constructing 'van-ban-goc' URL, fetching it, finding PDFs there.
    """
    content = ""
    try:
        # 1. Try Toàn Văn
        print(f"    Fetching: {url}")
        resp = requests.get(url, timeout=15, verify=False)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            content_div = soup.find("div", id="toanvancontent")
            if not content_div:
                content_div = soup.find("div", class_="content")
            
            if content_div:
                for tag in content_div(["script", "style", "iframe", "object"]):
                    tag.decompose()
                content = content_div.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"Error fetching detail {url}: {e}")

    # 2. Fallback if content is too short or empty
    if not content or len(content) < 500:
         print(f"  [Info] Content missing/short. Trying fallbacks...")
         
         urls_to_try = fallback_urls if fallback_urls else []
         
         # Logic: If we were on 'toanvan', try 'van-ban-goc' to find PDFs
         if "vbpq-toanvan.aspx" in url:
             vbg_url = url.replace("vbpq-toanvan.aspx", "vbpq-van-ban-goc.aspx")
             print(f"    [Fallback] Checking VanBanGoc page: {vbg_url}")
             try:
                 resp_vbg = requests.get(vbg_url, timeout=15, verify=False)
                 if resp_vbg.status_code == 200:
                     soup_vbg = BeautifulSoup(resp_vbg.content, 'html.parser')
                     
                     # 2a. Check Select Dropdown (ddrVanBanGoc)
                     # <select name="ddrVanBanGoc" ...> <option value="/FileData/...">...</option>
                     select_tag = soup_vbg.find("select", id="ddrVanBanGoc")
                     if select_tag:
                         options = select_tag.find_all("option")
                         for opt in options:
                             val = opt.get('value')
                             if val and val.lower().endswith('.pdf'):
                                 full_pdf = DOMAIN + val if val.startswith('/') else val
                                 if full_pdf not in urls_to_try:
                                     urls_to_try.append(full_pdf)
                     
                     # 2b. Check hidden download div (divShowDialogDownload) - generic ID
                     # HTML: <div id="divShowDialogDownload" ...>
                     dl_div = soup_vbg.find("div", id="divShowDialogDownload")
                     if dl_div:
                         # javascript:downloadfile('name','/path')
                         links = dl_div.find_all("a", href=True)
                         for lk in links:
                             href = lk['href']
                             if "downloadfile" in href:
                                 parts = href.split("','")
                                 if len(parts) >= 2:
                                     rel_path = parts[1].split("')")[0]
                                     full_dl = DOMAIN + rel_path
                                     if full_dl not in urls_to_try:
                                         urls_to_try.append(full_dl)
             except Exception as e:
                 print(f"    [Fallback] Error fetching VanBanGoc: {e}")

         # Process gathered PDF URLs
         for fb_url in urls_to_try:
             # Normalize URL
             if not fb_url.startswith('http'):
                 fb_url = DOMAIN + fb_url if fb_url.startswith('/') else fb_url
             
             # Check type
             if fb_url.lower().endswith('.pdf'):
                 pdf_text = extract_text_from_pdf_url(fb_url)
                 if pdf_text and len(pdf_text) > 500: # Ensure we got substantial text
                     print("    [Fallback] Successfully extracted text from PDF.")
                     return pdf_text
             
    return content

def crawl():
    results = []
    page = 1
    stop_crawl = False
    
    print(f"Starting crawl for years {TARGET_YEARS}...")
    
    while not stop_crawl:
        url = BASE_URL.format(page)
        print(f"Crawling Page {page}: {url}")
        
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                print("Failed to fetch page. Retrying once...")
                time.sleep(2)
                resp = requests.get(url, timeout=15)
                if resp.status_code != 200:
                    print("Failed. Stopping.")
                    break
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Find list items
            # From user HTML: <ul class="listLaw"> -> <li> -> <div class="item">
            list_law_ul = soup.find("ul", class_="listLaw")
            if not list_law_ul:
                print("No listLaw found. Structure might have changed or end of results.")
                break
                
            items = list_law_ul.find_all("li")
            if not items:
                print("No items found on this page.")
                break
            
            # Sub-loop for items
            items_processed_on_page = 0
            
            for li in items:
                div_item = li.find("div", class_="item")
                if not div_item: continue
                
                # Title & Link
                p_title = div_item.find("p", class_="title")
                if not p_title: continue
                
                a_tag = p_title.find("a")
                if not a_tag: continue
                
                title = a_tag.get_text(strip=True)
                link = a_tag.get('href', '')
                if link and not link.startswith('http'):
                    link = DOMAIN + link
                    
                # FIX: Always prefer "vbpq-toanvan.aspx" initially to try text extraction.
                # If only "vbpq-van-ban-goc.aspx" is provided, switch it.
                if "vbpq-van-ban-goc.aspx" in link:
                     link = link.replace("vbpq-van-ban-goc.aspx", "vbpq-toanvan.aspx")
                
                # FIX: Force "toanvan" (Full Text) URL if we got "van-ban-goc" (Original/PDF)
                # van-ban-goc page often has no selectable text or just embedded PDF.
                if "vbpq-van-ban-goc.aspx" in link:
                     link = link.replace("vbpq-van-ban-goc.aspx", "vbpq-toanvan.aspx")
                
                # Dates
                # <div class="right"> <p class="green"><label>Ban hành:</label>27/08/2025</p> ...
                div_right = div_item.find("div", class_="right")
                issuance_date_str = ""
                effective_date_str = ""
                
                if div_right:
                    # Parse all p tags
                    for p in div_right.find_all("p"):
                        text = p.get_text(strip=True) # e.g. "Ban hành:27/08/2025"
                        if "Ban hành:" in text:
                            issuance_date_str = text.split("Ban hành:")[-1].strip()
                        if "Hiệu lực:" in text:
                            effective_date_str = text.split("Hiệu lực:")[-1].strip()
                
                # Filter by Year
                issued_date = parse_date(issuance_date_str)
                if issued_date:
                    year = issued_date.year
                    if year in TARGET_YEARS:
                        # MATCH!
                        print(f"  [MATCH] {title} ({year})")
                        
                        # Extract Fallback URLs (Downloads)
                        fallback_urls = []
                        
                        # 1. From "Bản PDF" link
                        # <li class="source"><a href="...">Bản PDF</a></li>
                        li_source = div_item.find("li", class_="source")
                        if li_source:
                            a_source = li_source.find("a")
                            if a_source:
                                href = a_source.get('href', '')
                                # This link is usually a viewer page. Need to check if it leads to direct PDF or viewer.
                                # Often VBPL puts the direct PDF in subsequent logic. 
                                # For now, let's look for the HIDDEN DOWNLOAD DIV.
                                pass 

                        # 2. From "Tải về" hidden div
                        # The id is usually "divShowDialogDownload_" + ItemID
                        # We need item ID.
                        # href="/TW/Pages/vbpq-toanvan.aspx?ItemID=184189&dvid=13"
                        item_id_match = re.search(r'ItemID=(\d+)', link)
                        if item_id_match:
                            item_id = item_id_match.group(1)
                            download_div_id = f"divShowDialogDownload_{item_id}"
                            download_div = div_item.find("div", id=download_div_id)
                            
                            if download_div:
                                # Find all download links inside
                                # javascript:downloadfile('filename','/path/to/file')
                                sub_as = download_div.find_all("a", href=True)
                                for sub_a in sub_as:
                                    href = sub_a['href']
                                    if "downloadfile" in href:
                                        # Extract the second argument (URL)
                                        # Example: javascript:downloadfile('Thông tư...doc','/TW/Lists/vbpq/Attachments/184189/...')
                                        parts = href.split("','")
                                        if len(parts) >= 2:
                                            rel_path = parts[1].split("')")[0]
                                            full_dl_url = DOMAIN + rel_path
                                            fallback_urls.append(full_dl_url)
                        
                        # Fetch Full Content with Fallbacks
                        content_text = get_detail_content(link, fallback_urls=fallback_urls)
                        
                        results.append({
                            "title": title,
                            "url": link,
                            "issuance_date": issuance_date_str,
                            "effective_date": effective_date_str,
                            "year": year,
                            "content": content_text,
                            "source": "VBPL",
                            "type": "Luật",
                            "fallback_urls": fallback_urls
                        })
                        
                        items_processed_on_page += 1
                        time.sleep(0.5) # Polite delay
                    elif year < min(TARGET_YEARS):
                        # Found a law older than target range.
                        # Assuming chronological order (Mới đến cũ is default), we can stop.
                        print(f"  [STOP] Found older law: {year} < {min(TARGET_YEARS)}. Stopping.")
                        stop_crawl = True
                        break
                    else:
                        # Future year? Or just outside range (unlikely if 'Mới đến cũ')
                        pass
                else:
                    print(f"  [SKIP] Could not parse date: {issuance_date_str}")
            
            if items_processed_on_page == 0 and not stop_crawl:
                 # If we found 0 items on this page but didn't trigger stop (e.g. maybe mixed years or parsing error?), 
                 # we should check if we should continue.
                 # If we parsed dates and they were all > 2025 (impossible) or something.
                 # Let's assume if we found NO matches but haven't hit the 'old' year, we continue.
                 pass
            
            page += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break

    print(f"Crawl finished. Collected {len(results)} documents.")
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    crawl()

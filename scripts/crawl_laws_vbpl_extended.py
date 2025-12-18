
import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re
from datetime import datetime

# Logic: Crawl "Luật" from VBPL.vn
# Scope: Extended years (2015 - 2022)
# Base URL: https://vbpl.vn/TW/Pages/vanban.aspx?idLoaiVanBan=17&dvid=13

BASE_URL = "https://vbpl.vn/TW/Pages/vanban.aspx?idLoaiVanBan=17&dvid=13&Page={}"
DOMAIN = "https://vbpl.vn"
OUTPUT_FILE = r"e:\VSCODE_WORKSPACE\VNPT\data\laws_vbpl_2015_2022.json"
TARGET_YEARS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]

def parse_date(date_str):
    try:
        # Expected format: dd/mm/yyyy
        return datetime.strptime(date_str.strip(), "%d/%m/%Y")
    except ValueError:
        return None

def get_detail_content(url):
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return ""
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        content_div = soup.find("div", id="toanvancontent")
        if not content_div:
            content_div = soup.find("div", class_="content")
        
        if content_div:
            # Clean
            for tag in content_div(["script", "style", "iframe", "object"]):
                tag.decompose()
            return content_div.get_text(separator="\n", strip=True)
        
        return ""
        
    except Exception as e:
        print(f"Error fetching detail {url}: {e}")
        return ""

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
                
                # Dates
                div_right = div_item.find("div", class_="right")
                issuance_date_str = ""
                effective_date_str = ""
                
                if div_right:
                    for p in div_right.find_all("p"):
                        text = p.get_text(strip=True)
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
                        
                        content_text = get_detail_content(link)
                        
                        results.append({
                            "title": title,
                            "url": link,
                            "issuance_date": issuance_date_str,
                            "effective_date": effective_date_str,
                            "year": year,
                            "content": content_text,
                            "source": "VBPL",
                            "type": "Luật"
                        })
                        
                        items_processed_on_page += 1
                        time.sleep(0.5)
                    elif year < min(TARGET_YEARS):
                        # Found a law older than target range.
                        print(f"  [STOP] Found older law: {year} < {min(TARGET_YEARS)}. Stopping.")
                        stop_crawl = True
                        break
                    else:
                        # Newer year (e.g. 2023, 2024, 2025) -> Pass
                        pass
                else:
                    # Could not parse date
                    pass
            
            # Save progress every page
            if items_processed_on_page > 0 or page % 5 == 0:
                 print(f"  Saved {len(results)} items so far...")
            
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

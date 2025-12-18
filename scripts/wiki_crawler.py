import os
import json
import re
import unicodedata
import time
import hashlib
import random
import requests
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import wikipediaapi
    from bs4 import BeautifulSoup, NavigableString
    from tqdm.notebook import tqdm
except ImportError:
    os.system("pip install -q wikipedia-api beautifulsoup4 tqdm")
    import wikipediaapi
    from bs4 import BeautifulSoup, NavigableString
    from tqdm.notebook import tqdm
logging.getLogger("urllib3").setLevel(logging.ERROR)

USER_AGENT = "VNPT_DeepData/27.0 (Cleaner_Engine; contact: thaison_ds)"
ROOT_DIR = "vnpt_data_clean"
INPUT_PATH = "categories.json"
MAX_WORKERS = 30
TARGET_DOCS = 10000
MAX_DEPTH = 10
MAX_ITEMS_PER_CAT = 100

DEFAULT_ROOTS = [
    "Thể loại:Y học",
    "Thể loại:Y học lâm sàng",
    "Thể loại:Y học cơ sở",
    "Thể loại:Bệnh",
    "Thể loại:Bệnh theo cơ quan",
    "Thể loại:Triệu chứng y học",
    "Thể loại:Chẩn đoán y học",
    "Thể loại:Điều trị học",
    "Thể loại:Dược học",
    "Thể loại:Dược phẩm",
    "Thể loại:Thuốc",
    "Thể loại:Nhóm thuốc",
    "Thể loại:Dinh dưỡng",
    "Thể loại:Chất dinh dưỡng",
    "Thể loại:Vitamin",
    "Thể loại:Hợp chất sinh học",
    "Thể loại:Giải phẫu học",
    "Thể loại:Hệ cơ quan",
    "Thể loại:Sinh lý học",
    "Thể loại:Miễn dịch học",
    "Thể loại:Vi sinh vật học",
    "Thể loại:Ký sinh trùng học",
    "Thể loại:Ung thư",
    "Thể loại:Bệnh tim mạch",
    "Thể loại:Sức khỏe tâm thần"
]

wiki = wikipediaapi.Wikipedia(
    user_agent=USER_AGENT,
    language='vi',
    extract_format=wikipediaapi.ExtractFormat.WIKI
)

final_cat_file = None

if os.path.exists(INPUT_PATH):
    if os.path.isfile(INPUT_PATH):
        final_cat_file = INPUT_PATH
    elif os.path.isdir(INPUT_PATH):
        for f_name in os.listdir(INPUT_PATH):
            if f_name.endswith('.json'):
                final_cat_file = os.path.join(INPUT_PATH, f_name)
                break

ROOT_CATEGORIES = []
if final_cat_file:
    try:
        with open(final_cat_file, 'r', encoding='utf-8') as f:
            ROOT_CATEGORIES = json.load(f)
        print(f"FOUND CONFIG FILE: {final_cat_file}")
        print(f"LOADED {len(ROOT_CATEGORIES)} CATEGORIES.")
    except:
        ROOT_CATEGORIES = DEFAULT_ROOTS
else:
    print("NO JSON FILE FOUND IN INPUT. USING DEFAULTS.")
    ROOT_CATEGORIES = DEFAULT_ROOTS

session = requests.Session()
adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=Retry(total=3, backoff_factor=0.5))
session.mount("https://", adapter)
session.headers.update({"User-Agent": USER_AGENT})

def extract_clean_content(url):
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200: return ""
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        content_div = soup.find("div", class_="mw-parser-output")
        if not content_div: return ""

        for tag in content_div.find_all(['script', 'style', 'noscript', 'iframe', 'object']):
            tag.decompose()
        
        for tag in content_div.find_all(class_=['mw-editsection', 'reference', 'noprint', 'infobox', 'navbox', 'reflist', 'metadata', 'thumb', 'tright', 'tleft', 'sidebar']):
            tag.decompose()

        for math_tag in content_div.find_all("span", class_="mwe-math-element"):
            tex_node = math_tag.find("annotation", encoding="application/x-tex")
            if tex_node:
                tex_content = tex_node.get_text().strip()
                math_tag.replace_with(f" $${tex_content}$$ ")
            else:
                math_tag.decompose()

        clean_text_parts = []
        stop_headers = ['tham khảo', 'liên kết ngoài', 'xem thêm', 'chú thích', 'nguồn', 'tài liệu']

        for element in content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'dl', 'blockquote']):
            text = element.get_text(separator=' ', strip=True)
            text = unicodedata.normalize('NFKC', text)
            
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                if any(sh in text.lower() for sh in stop_headers):
                    break
                continue 

            if not text: continue
            
            text = re.sub(r'\[\d+\]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            if len(text) > 10:
                clean_text_parts.append(text)

        final_text = "\n".join(clean_text_parts)
        return final_text if len(final_text) > 200 else ""

    except Exception:
        return ""

def create_record(title, content, url, category):
    return json.dumps({
        "id": hashlib.md5(url.encode()).hexdigest(),
        "subcategory": category.replace("Thể loại:", ""),
        "title": title,
        "content": content,
        "url": url
    }, ensure_ascii=False)

class DeepSpider:
    def __init__(self):
        self.visited_titles = set()
        self.visited_cats = set()

    def run(self):
        if os.path.exists(ROOT_DIR): shutil.rmtree(ROOT_DIR)
        os.makedirs(ROOT_DIR)
        
        queue = [(cat, 0) for cat in ROOT_CATEGORIES]
        collected_count = 0
        output_file = os.path.join(ROOT_DIR, "clean_data.jsonl")
        
        with open(output_file, 'w', encoding='utf-8') as f_out:
            pbar = tqdm(total=TARGET_DOCS, unit="doc", colour='green')
            
            while queue and collected_count < TARGET_DOCS:
                current_cat, depth = queue.pop(0)
                
                if current_cat in self.visited_cats: continue
                self.visited_cats.add(current_cat)

                try:
                    cat_page = wiki.page(current_cat)
                    if not cat_page.exists(): continue
                    
                    members = list(cat_page.categorymembers.values())
                    pages_to_fetch = []
                    
                    for m in members:
                        if m.ns == wikipediaapi.Namespace.MAIN:
                            if m.title not in self.visited_titles:
                                pages_to_fetch.append(m)
                                self.visited_titles.add(m.title)
                    
                    if depth < MAX_DEPTH:
                        subcats = [m for m in members if m.ns == wikipediaapi.Namespace.CATEGORY]
                        random.shuffle(subcats)
                        for sc in subcats:
                            queue.append((sc.title, depth + 1))

                    if pages_to_fetch:
                        random.shuffle(pages_to_fetch)
                        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                            futures = []
                            for p in pages_to_fetch[:MAX_ITEMS_PER_CAT]: 
                                futures.append(executor.submit(self._process_page, p, current_cat))
                            
                            for f in as_completed(futures):
                                res = f.result()
                                if res:
                                    f_out.write(res + '\n')
                                    collected_count += 1
                                    pbar.update(1)
                                    if collected_count >= TARGET_DOCS: break
                except: continue
            
            pbar.close()

    def _process_page(self, page, cat_name):
        try:
            content = extract_clean_content(page.fullurl)
            if content:
                return create_record(page.title, content, page.fullurl, cat_name)
        except: return None

spider = DeepSpider()
spider.run()

shutil.make_archive("vnpt_data_clean", 'zip', ROOT_DIR)
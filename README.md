# VNPT AI Hackathon 2024 - RAG Pipeline (Track 2)

Hệ thống RAG (Retrieval-Augmented Generation) tiên tiến dành cho cuộc thi VNPT AI Hackathon, được thiết kế để giải quyết các câu hỏi đa lĩnh vực (Luật, Khoa học xã hội, Tự nhiên, Kinh tế) với độ chính xác cao dựa trên kỹ thuật Hybrid Search và suy luận logic.

## 1. Kiến trúc Hệ thống (System Architecture)

Hệ thống hoạt động theo quy trình 3 bước (3-Stage Pipeline):

### Stage 1: Phân loại & Định tuyến (Router)
- **Input:** Câu hỏi trắc nghiệm.
- **Xử lý:** Sử dụng LLM để phân loại câu hỏi vào các domain (Luật, Kinh tế, Vĩ mô, Xã hội, Tự nhiên...).
- **Tác dụng:**
    - Kích hoạt prompt chuyên biệt cho từng loại (Ví dụ: Prompt Luật ưu tiên trích dẫn điều khoản, Prompt Xã hội ưu tiên tư duy phạm trù).
    - Giúp LLM áp dụng đúng "Tư duy giải quyết vấn đề" (Problem Solving Mindset) phù hợp với lĩnh vực.

### Stage 2: Truy xuất Thông tin Lai ghép (Hybrid Retrieval)
Hệ thống sử dụng cơ chế tìm kiếm đa chiều để đảm bảo không bỏ sót thông tin:
- **Semantic Search (Vector):** Sử dụng `ChromaDB` với mô hình embedding của VNPT để tìm kiếm ngữ nghĩa.
- **Keyword Search (BM25):** Sử dụng `SQLite FTS5` để bắt chính xác từ khóa chuyên ngành (số hiệu luật, tên riêng).
- **Reciprocal Rank Fusion (RRF):** Hợp nhất kết quả từ hai nguồn trên.
- **Reranking:** Sử dụng Cross-Encoder (`BAAI/bge-reranker-base`) để chấm điểm lại top 50 văn bản và chọn ra 5-10 văn bản sát nhất.

### Stage 3: Suy luận & Trả lời (Inference)
- **Zero-shot / Few-shot CoT:** Sử dụng kỹ thuật Chain-of-Thought để yêu cầu mô hình suy luận từng bước trước khi chọn đáp án.
- **Self-Correction:** Cơ chế tự kiểm tra các bẫy logic (Chronological Error, Redefinition Trap) trong prompt.

---

---

## 2. Quy trình Xử lý Dữ liệu (Data Processing Pipeline)

Hệ thống vận hành một dây chuyền xử lý dữ liệu tự động hóa cao, từ thu thập (Crawling) đến làm sạch (Cleaning) và đánh chỉ mục (Indexing).

### 2.1. Thu thập Dữ liệu (Crawling)
Các script trong thư mục `crawlers/` đảm nhiệm việc tải dữ liệu từ các nguồn chính thống:

| Script Name | Mục tiêu (Target) | Nguồn (Source) | Mô tả |
| :--- | :--- | :--- | :--- |
| `crawl_laws_vbpl.py` | Văn bản Luật | *vbpl.vn* | Tải toàn bộ Luật, Pháp lệnh, Nghị quyết còn hiệu lực. |
| `crawl_decrees_*.py` | Nghị định | *vbpl.vn, luatvietnam.vn* | Tải và phân loại Nghị định theo cơ quan ban hành. |
| `crawl_dvc_*.py` | Dịch vụ công | *dichvucong.gov.vn* | Thu thập quy trình thực hiện thủ tục hành chính. |
| `crawl_provinces_wiki.py` | Địa lý | *vi.wikipedia.org* | Tải thông tin tự nhiên, kinh tế của 63 tỉnh thành. |
| `crawl_economics_voer.py` | Kinh tế học | *voer.edu.vn* | Thu thập giáo trình kinh tế vĩ mô/vi mô. |

### 2.2. Làm sạch & Chuẩn hóa (Cleaning & Normalization)
Sau khi thu thập, dữ liệu thô (Raw HTML/PDF) được đưa qua pipeline làm sạch trong `process_data/`:

| Processor Script | Đầu vào (Input) | Đầu ra (Output) | Tác vụ Xử lý (Operations) |
| :--- | :--- | :--- | :--- |
| `process_merger_data.py` | Luật/Nghị định (Raw) | `law_merged.jsonl` | Gộp các bản sửa đổi, loại bỏ điều khoản hết hiệu lực. |
| `process_ho_chi_minh_data.py` | Giáo trình PDF | `hcm_ideology.jsonl` | OCR, sửa lỗi chính tả tiếng Việt, tách đoạn theo ý. |
| `process_dialy_hsg.py` | Sách giáo khoa Địa | `geo_knowledge.jsonl` | Trích xuất bảng số liệu thành text mô tả (Table-to-Text). |
| `process_dictionaries.py` | Từ điển | `dictionary.jsonl` | Cấu trúc hóa định nghĩa cho bài toán giải nghĩa từ. |

*   **Chunking Strategy:**
    *   **Legal:** Chia theo Điều khoản (Article-based). Giữ nguyên số hiệu (Ví dụ: "Điều 5. Nguyên tắc...").
    *   **Textbook:** Chia theo đoạn văn (Semantic Chunking) kích thước 512-1024 tokens, overlap 10%.

### 2.3. Lưu trữ & Indexing
Cuối cùng, dữ liệu sạch được index bởi `scripts/indexer.py`:
1.  **Vector Index (ChromaDB):** Sử dụng model embedding VNPT (`vnptai_hackathon_embedding`) để mã hóa ngữ nghĩa.
2.  **Keyword Index (SQLite FTS5):** Tokenize tiếng Việt (dùng `pyvi`) để phục vụ tìm kiếm từ khóa chính xác (BM25).

---

## 3. Giải pháp & Hiệu quả (Solution & Performance)

### Tại sao lại chọn Kiến trúc này?
1.  **Vấn đề:** Các câu hỏi pháp luật yêu cầu độ chính xác tuyệt đối về số liệu/tên văn bản (BM25 làm tốt), nhưng các câu hỏi xã hội lại cần hiểu ngữ cảnh trừu tượng (Vector làm tốt).
    -> **Giải pháp:** **Hybrid Search** kết hợp cả hai thế mạnh, bù trừ khiếm khuyết cho nhau.
2.  **Vấn đề:** Tìm kiếm nhiều mang lại nhiều nhiễu (Top K=50), làm loãng ngữ cảnh của LLM.
    -> **Giải pháp:** **Cross-Encoder Reranker** đóng vai trò "Bộ lọc tinh", chỉ giữ lại 5-10 đoạn văn bản chất lượng nhất để đưa vào Prompt, giúp tăng độ chính xác lên 20-30%.
3.  **Vấn đề:** Mô hình LLM nhỏ thường hay ảo giác hoặc suy luận sai các bẫy logic.
    -> **Giải pháp:** **Structured Prompting (CoT)** ép mô hình phải "nghĩ trước khi làm", kết hợp với các luật cấm (Negative Constraints) để tránh các lỗi sơ đẳng.

### Tối ưu Hiệu năng (Efficiency)
-   **Concurrency:** Sử dụng `ThreadPoolExecutor` để chạy song song 2 luồng tìm kiếm (Vector & BM25) -> Giảm 50% thời gian truy xuất.
-   **Batch Processing:** Xử lý câu hỏi theo lô (Batch) giúp tận dụng tối đa băng thông mạng và giảm overhead của HTTP request.
-   **Lazy Loading:** Các model nặng (như Reranker, Tokenizer) chỉ được load khi thật sự cần thiết và giữ trong RAM (Singleton Pattern).

---

## 4. Kiến trúc Agent Chuyên sâu (Agentic Architecture Deep Dive)

Hệ thống được thiết kế theo mô hình **Compound AI System**, trong đó LLM đóng vai trò là bộ não điều phối các công cụ (Tools) và luồng dữ liệu (Data Flow).

### 3.1. Quy trình Xử lý 3 Lớp (3-Pass Execution Flow)
Thay vì gọi LLM một lần duy nhất, Agent thực hiện 3 vòng lặp để tối ưu kết quả:

1.  **Pass 1: Mass Inference (Suy luận Diện rộng)**
    *   Sử dụng **Small Model** để xử lý song song toàn bộ các câu hỏi.
    *   Chia nhỏ câu hỏi thành các Batch theo Domain để tận dụng Context Caching.
    *   Mục tiêu: Đạt tốc độ tối đa và độ phủ 80% câu hỏi dễ/trung bình.

2.  **Pass 2: Tool-Assisted Logic (Công cụ Bổ trợ)**
    *   Hệ thống cho phép LLM gọi công cụ (Tool Use) nếu thấy thiếu thông tin hoặc cần tính toán:
        *   **Retrieval Tool:** Tra cứu bổ sung từ khóa mới nếu ngữ cảnh ban đầu chưa đủ.
        *   **Calculation Tool:** Thực hiện phép tính Toán/Lý/Hóa chính xác tuyệt đối bằng Python.
    *   Kết quả từ Tool được "Inject" ngược lại vào ngữ cảnh để LLM suy luận lại.
    
3.  **Pass 3: Reliability Retry (Xử lý Ngoại lệ)**
    *   Cơ chế **Gap Filling** tự động phát hiện các câu hỏi bị bỏ sót (do lỗi mạng, lỗi parse JSON, hoặc Rate Limit).
    *   **Private Mode:** Retry từng câu (Single Shot) để đảm bảo độ chính xác cao nhất.
    *   **Public Mode:** Retry theo Batch nhỏ để tiết kiệm request nhưng vẫn đảm bảo điền đủ đáp án.

### 3.2. Hệ thống Định tuyến & Prompting (Router & Strategy Pattern)
Trong `src/domain_prompts.py`, chúng tôi cài đặt Strategy Pattern để định tuyến câu hỏi:

### 3.2. Hệ thống Định tuyến & Prompting (Router & Strategy Pattern)
Trong `src/domain_prompts.py`, chúng tôi cài đặt Strategy Pattern để định tuyến câu hỏi tới đúng chuyên gia:

| Mã | Domain | Chiến lược Prompting (Strategy) | Nguyên tắc Cốt lõi (Core Principles) |
| :--- | :--- | :--- | :--- |
| **XH** | **Xã hội (Social)** | *Ontological Thinking* (Tư duy Bản thể) | Tìm kiếm bản chất/định nghĩa nội tại (Gốc), bỏ qua các yếu tố tác động bên ngoài (Ngọn). |
| **KT** | **Kinh tế - Luật** | *Rule-Based & Substance Over Form* | Thượng tôn văn bản pháp luật. Với kế toán/thuế: Ưu tiên bản chất kinh tế hơn hình thức. |
| **TN** | **Tự nhiên** | *Step-by-Step Reasoning* | Yêu cầu giải trình các bước tính toán, không chấp nhận kết quả cuối cùng ngay lập tức. |
| **ST** | **Chiến lược & Hệ thống** | *Abstract System Thinking* | **Toxic Component Rule**: Một phương án chỉ cần chứa 1 thành phần sai (nghịch lý hệ thống) là sai toàn bộ. |
| **DL** | **Địa lý** | *Spatial + Systems Thinking* | Kết hợp tư duy không gian (Vùng miền) và quy luật tương tác (Tự nhiên làm nền, KT-XH quyết định). |
| **NV** | **Văn học** | *Aesthetic Thinking* | Phân biệt Nội dung vs Nghệ thuật. Tư duy "Điển hình hóa" (Chi tiết phục vụ chủ đề). |
| **TG** | **Tôn giáo** | *Functional Separation* | Phân biệt vai trò "Khởi tạo vật lý" (người xây) vs "Tiếp nối tâm linh" (trụ trì). |
| **RC** | **Đọc hiểu** | *Structure over Chronology* | Giải quyết tham chiếu (Reference Resolution) dựa trên cấu trúc ngữ pháp trước logic thời gian. |
| **K** | **Kiến thức chung** | *Common Sense & Truth* | Ưu tiên sự thật phổ quát. Chống Hallucination bằng cách kiểm chứng chéo. |
| **S** | **Nhạy cảm** | *Safety Guardrails* | Kiểm duyệt từ khóa chính trị/tôn giáo/phi pháp. Ưu tiên từ chối nếu phát hiện ý định xấu. |


### 3.3. Fault Tolerance & Heuristics (Khả năng chịu lỗi)
Do LLM đầu ra thường không ổn định (Hallucination hoặc Malformed JSON), hệ thống trang bị lớp `text_utils.py` để xử lý hậu kỳ:
*   **Regex Salvaging:** Nếu JSON bị lỗi cú pháp, hệ thống dùng Regex để "cứu" các trường dữ liệu quan trọng (ID, Answer) thay vì vứt bỏ toàn bộ.
*   **Heuristic Mapping:** Tự động chuẩn hóa câu trả lời (ví dụ: "Answer is A" -> "A") để đảm bảo tính nhất quán cho file submission.

---

## 5. Công nghệ Sử dụng (Tech Stack)

*   **Ngôn ngữ:** Python 3.10+
*   **Vector Database:** ChromaDB (Persistent Disk Storage).
*   **Text Search:** SQLite FTS5 (Triển khai BM25 nhanh và nhẹ).
*   **LLM API:** VNPT AI Hackathon API (Large/Small/Embedding).
*   **Libraries chính:**
    - `requests`, `tenacity`: Gọi API và xử lý Retry.
    - `sentence-transformers`: Reranking (Optional).
    - `pyvi`: Tokenizer tiếng Việt.
    - `numpy`, `pandas`: Xử lý dữ liệu.

---

## 6. Cấu trúc Thư mục

```
VNPT-HACKATHON/
├── api_keys/               # Chứa file api-keys.json (Cần tạo thủ công)
├── crawlers/               # Bộ công cụ thu thập dữ liệu (VBPL, Wikipedia)
├── data/                   # Dữ liệu nguồn (Knowledge Base cho RAG)
├── docs/                   # Tài liệu hướng dẫn & Quy định cuộc thi
├── output/                 # Nơi chứa kết quả (submission.json)
├── process_data/           # Script xử lý & làm sạch dữ liệu thô (Raw -> JSONL)
├── public_test/            # Đề thi công khai (test.json)
├── scripts/                # Các script tiện ích
│   ├── indexer.py          # Script tạo Index (Vector + BM25)
│   ├── test_single_question.py # Script debug nhanh 1 câu hỏi
│   └── switch_config.py    # Script chuyển đổi Public/Private mode
├── src/                    # Source code lõi (Core Logic)
│   ├── api.py              # Client gọi API VNPT (Retry, Timeout)
│   ├── batch_solver.py     # Luồng giải đề chính (3-Pass Flow)
│   ├── retriever.py        # Logic tìm kiếm (Hybrid Search + Rerank)
│   ├── vector_store.py     # Wrapper ChromaDB
│   ├── text_utils.py       # Xử lý chuỗi & Regex salvaging
│   ├── config.py           # File cấu hình (được ghi đè bởi switch_config)
│   └── prompts/            # Hệ thống Prompt kỹ thuật cao (Domain-specific)
├── .gitignore              # Cấu hình bỏ qua file rác/nhạy cảm
├── DATA_ORIGIN.md          # Ghi chú nguồn gốc dữ liệu
├── Dockerfile              # Cấu hình môi trường Docker chuẩn BTC
├── inference.sh            # Script chạy chính thức (Entrypoint cho Docker)
├── predict.py              # Code Python chạy End-to-End
├── requirements.txt        # Danh sách thư viện phụ thuộc
└── domain_cache.json       # Cache kết quả phân loại (Tăng tốc độ)
```

---

## 7. Hướng dẫn Cài đặt & Tái lập (Setup & Reproduction)

### Bước 1: Cài đặt Môi trường
```bash
pip install -r requirements.txt
```
*Lưu ý: Để chạy Reranker hiệu quả, khuyến nghị sử dụng máy có GPU (CUDA).*

### Bước 2: Cấu hình API Key
Tạo file `api_keys/api-keys.json` với cấu trúc sau. Bạn cần điền đầy đủ 3 loại key (Small, Large, Embeddings):

```json
[
  {
    "llmApiName": "LLM small",
    "authorization": "Bearer <YOUR_TOKEN>",
    "tokenId": "<YOUR_TOKEN_ID>",
    "tokenKey": "<YOUR_TOKEN_KEY>"
  },
  {
    "llmApiName": "LLM large",
    "authorization": "Bearer <YOUR_TOKEN>",
    "tokenId": "<YOUR_TOKEN_ID>",
    "tokenKey": "<YOUR_TOKEN_KEY>"
  },
  {
    "llmApiName": "LLM embedings",
    "authorization": "Bearer <YOUR_TOKEN>",
    "tokenId": "<YOUR_TOKEN_ID>",
    "tokenKey": "<YOUR_TOKEN_KEY>"
  }
]
```

### Bước 3: Chế độ Public vs Private
Hệ thống hỗ trợ 2 chế độ chạy với chiến lược xử lý khác nhau:

| Tham số (Config) | **Private Mode (Official)** | **Public Mode (Safe)** | Giải thích |
| :--- | :--- | :--- | :--- |
| **Rate Limit** | 10,000 req/h (Turbo) | < 60 req/h (Low) | Public API giới hạn rất chặt, Private API (BTC cấp) gần như không giới hạn. |
| **Batch Size** | 1 (Single Shot) | 10-20 | Private mode xử lý từng câu để tối ưu chính xác (Accuracy). Public mode gom nhóm để tiết kiệm request. |
| **Retriever K** | Top 10 Docs | Top 5 Docs | Private mode lấy nhiều ngữ cảnh hơn. |
| **GPU Workers** | Dynamic (Auto-detect) | Fixed (3) | Private mode tự động tận dụng tối đa VRAM. Public mode giới hạn để tránh OOM khi test local. |

**Cách chuyển đổi:**
Sử dụng script tiện ích có sẵn để chuyển đổi nhanh:

```bash
# Chuyển sang chế độ Public (Safe Mode) - Dùng khi test ở nhà
python scripts/switch_config.py public

# Chuyển sang chế độ Private (Turbo Mode) - Dùng khi nộp bài
python scripts/switch_config.py private
```

### Bước 4: Chuẩn bị Dữ liệu & Indexing
Copy toàn bộ dữ liệu `.json/.jsonl` vào thư mục `data/`. Sau đó chạy lệnh index:
```bash
python scripts/indexer.py
```
*Quá trình này sẽ tạo ra `chroma_db` (Vector) và `bm25_index.db` (Keyword).*

---

## 8. Quy trình Chạy End-to-End (Submission Pipeline)

Để tạo file kết quả nộp bài (`submission.json`) từ file đề thi (`test.json`):

1.  **Cấu hình đường dẫn:**
    Mở file `predict.py`, kiểm tra biến `input_path` và `output_path` đã trỏ đúng đến file `test.json` của bạn và nơi muốn lưu kết quả.

3.  **Chạy lệnh (Standard Mode):**
    Sử dụng script `inference.sh` để đảm bảo quy trình chuẩn (tự động kiểm tra index):
    ```bash
    bash inference.sh
    ```
    *Lưu ý: Script này tương thích hoàn toàn với môi trường Docker của BTC.*

4.  **Chạy lệnh thủ công (Manual Mode):**
    ```bash
    # Chạy trực tiếp python (tự động fallback về local config nếu không tìm thấy file hệ thống)
    python predict.py --input public_test/test.json --output output/submission.json
    ```

3.  **Kiểm tra kết quả:**
    File kết quả sẽ được lưu tại `output/submission.json`.

---

## 9. Các Script Hỗ trợ (Utility)

*   **Test nhanh 1 câu hỏi:**
    Sửa nội dung câu hỏi trong `scripts/test_single_question.py` và chạy:
    ```bash
    python scripts/test_single_question.py
    ```
    *Dùng để debug logic suy luận của model.*

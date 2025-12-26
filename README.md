# VNPT AI Hackathon 2025: Báo Cáo Kỹ Thuật & Tài Liệu Hệ Thống

**Đội thi:** Duel Warrior 
```text
Phan Đặng Thái Sơn (2007)
Hoàng Chí Tâm (2007)
```
**Phiên bản:** 1.0.0 (Submission v1)

## 1. Tổng quan Hệ thống (System Overview)

Hệ thống được thiết kế dựa trên kiến trúc **RAG (Retrieval-Augmented Generation)** lai ghép nâng cao (Advanced Hybrid RAG), nhằm giải quyết bài toán đa lĩnh vực (Luật, Kinh tế, Xã hội, Tự nhiên) với hai mục tiêu tối thượng:
1.  **Độ chính xác (Precision):** Loại bỏ ảo giác (Hallucination) thông qua truy xuất dữ liệu định danh (Identity-based Retrieval).
2.  **Khả năng tổng quát hóa (Generalization):** Xử lý các câu hỏi suy luận trừu tượng thông qua kỹ thuật Prompt Engineering cấu trúc.

---

## 2. Kiến trúc & Luồng Dữ liệu (Architecture & Data Flow)

Hệ thống hoạt động theo mô hình xử lý tuần tự (Sequential Pipeline) với sự hỗ trợ của các module chuyên biệt.

### Sơ đồ Luồng hoạt động (Private Mode - High Performance)

Trong chế độ **Private Mode**, hệ thống kích hoạt toàn bộ sức mạnh tính toán để xử lý sâu từng câu hỏi:

```text
[INPUT QUERY] (Single Request / Batch)
      |
      v
[DOMAIN ROUTER] (LLM-based Zero-shot Classifier)
      |
      |  --- Classify into 10 Experts ---
      +--> [XH] Khoa hoc Xa hoi       +--> [NV] Van hoc
      +--> [KT] Kinh te - Luat        +--> [TG] Ton giao
      +--> [TN] Khoa hoc Tu nhien     +--> [RC] Doc hieu (Reading)
      +--> [ST] Chien luoc - He thong +--> [DL] Dia ly
      +--> [K]  Kien thuc chung       +--> [S]  Nhay cam (Safe)
      |
      v
[CONTEXT RETRIEVAL STRATEGY] (Private Mode: Max Concurrency)
      |
      +--(Thread 1)--> [VECTOR SEARCH] (ChromaDB) --+
      |                (Recall Top-30 Deep Semantic)|
      |                                             v
      +--(Thread 2)--> [KEYWORD SEARCH] (BM25) -----+
      |                (Recall Top-30 Exact Match)  |
      |                                             |
      +------------------------------------------- > [RRF FUSION]
                                                    |
                                                    v
                                          [CROSS-ENCODER RERANKER]
                                          (Filter Top-10 High Precision)
                                                    |
                                                    v
      +---------------------------------------------+
      |
      v
[GENERATIVE REASONING LOOP] (Agentic Flow)
      |
      |             (Loop: Context Updated)
      |           +---------------------------+
      |           |                           |
      v           v                           |
      [LLM THINKING]                          |
      (Small Model)                           |
           |                                  |
           v                                  |
      < NEED TOOL? > ----- YES ----> [TOOL EXECUTION]
           |                        (Python / Search)
           |
           NO
           |
           v
[FINAL ANSWER GENERATION]
```

### Chi tiết các tầng xử lý:

1.  **Input Processing:** Tiền xử lý văn bản, chuẩn hóa ID câu hỏi.
2.  **Dynamic Routing:** Phân loại câu hỏi vào 1 trong 10 nhóm domain (Luật, Kinh tế, Địa lý, Toán,...) để áp dụng chiến lược suy luận (Reasoning Strategy) phù hợp.
3.  **Hybrid Retrieval Core:**
    *   Truy vấn song song (Parallel Execution) vào Vector Database và Keyword Database.
    *   Hợp nhất kết quả bằng thuật toán **RRF (Reciprocal Rank Fusion)** để cân bằng giữa độ tương đồng ngữ nghĩa và độ khớp từ khóa.
4.  **Re-ranking:** Đánh giá lại độ phù hợp của văn bản bằng mô hình Cross-Encoder, lọc nhiễu triệt để.
5.  **Generative Inference:** LLM sinh câu trả lời dựa trên ngữ cảnh đã được làm sạch và Prompt đặc tả.

---

## 3. Thuật toán & Kỹ thuật Áp dụng (Applied Algorithms)

Chúng tôi áp dụng các thuật toán đã được chứng minh hiệu quả trong các bài toán IR (Information Retrieval) và NLP:

### 3.1. Hybrid Search (Tìm kiếm Lai ghép)
Để giải quyết bài toán "Lexical Gap" (Khoảng cách từ vựng) trong các văn bản pháp luật và "Semantic Gap" (Khoảng cách ngữ nghĩa) trong văn bản xã hội:
*   **Dense Retrieval:** Sử dụng `ChromaDB` với mô hình embedding `vnptai_hackathon_embedding`.
    *   *Ưu điểm:* Bắt được ngữ nghĩa ẩn (ví dụ: "vũ khí nóng" $\approx$ "súng").
*   **Sparse Retrieval:** Sử dụng thuật toán **Okapi BM25** (cài đặt qua SQLite FTS5 + Tokenizer `pyvi`).
    *   *Ưu điểm:* Bắt chính xác các thực thể định danh (Named Entity) như số hiệu nghị định, tên riêng địa danh.
*   **Fusion Strategy:** Kết hợp kết quả $R_{vector}$ và $R_{bm25}$ thông qua công thức RRF:
    $$Score(d) = \sum_{r \in R} \frac{1}{k + rank(d, r)}$$
    *(Với hằng số k=60 để giảm thiểu tác động của các outlier).*

### 3.2. Cross-Encoder Re-ranking
*   **Vấn đề:** Các thuật toán Bi-Encoder (Retrieval) nhanh nhưng độ chính xác thấp ở Top-50.
*   **Giải pháp:** Sử dụng mô hình `BAAI/bge-reranker-base` (Cross-Encoder) để tính toán ma trận Attention đầy đủ giữa Query và Document.
*   **Hiệu quả:** Tăng độ chính xác (Precision@5) lên ~15-20% so với chỉ dùng Retrieval thông thường, đảm bảo LLM chỉ nhận được thông tin tinh khiết nhất.

### 3.3. Phân tích Thời gian Phản hồi (Inference Time Analysis)

Chúng tôi đã tối ưu hóa kỹ lưỡng để đảm bảo hệ thống phản hồi nhanh chóng (dưới 10s) ngay cả trong chế độ Private Mode:

| Giai đoạn (Stage) | Thời gian (Latency) | Kỹ thuật Tối ưu (Optimization) |
| :--- | :--- | :--- |
| **1. Routing** | ~0.5s | Zero-shot Classification với Caching domain. |
| **2. Retrieval** | ~0.8s | Xử lý song song (Multi-threading) Chroma + SQLite. |
| **3. Reranking** | ~0.2s | Batch Inference trên GPU (Quantized FP16). |
| **4. Inference** | ~4.0s - 6.0s | Streaming Token & CoT (Tùy độ dài câu trả lời). |
| **TỔNG CỘNG** | **~ 6.0s / câu** | **Nhanh gấp 10 lần** ngưỡng timeout thông thường (60s). |

---

## 4. Kỹ thuật Prompt Engineering: Trừu tượng hóa & Tổng quát hóa

Thay vì sử dụng các Prompt cứng nhắc ("Hãy trả lời câu này"), hệ thống áp dụng các kỹ thuật Prompting tiên tiến nhằm kích thích khả năng tư duy bậc cao của mô hình.

### 4.1. Nguyên tắc Trừu tượng hóa (Principle of Abstraction)
Hệ thống không yêu cầu LLM ghi nhớ kiến thức, mà yêu cầu LLM **trích xuất quy luật** từ ngữ cảnh được cung cấp.
*   *Ví dụ (Môn Địa lý):* Thay vì hỏi "Tỉnh A trồng cây gì?", Prompt yêu cầu: "Dựa trên điều kiện thổ nhưỡng (Đất feralit/phù sa) và khí hậu trong ngữ cảnh, hãy suy luận loại cây trồng công nghiệp phù hợp theo quy luật sinh học."

### 4.2. Tư duy Hệ thống (System Thinking) trong Prompt
Đối với các câu hỏi Chiến lược hoặc Hệ thống, Prompt được thiết kế để phát hiện **nghịch lý (Paradox)**:
*   **Mẫu Prompt:** "Một hệ thống chỉ đúng khi mọi thành phần con đều đúng. Nếu phát hiện một mệnh đề con trong đáp án mâu thuẫn với Nguyên lý X trong ngữ cảnh, hãy loại bỏ ngay lập tức (Toxic Component Rule)."
*   **Hiệu quả:** Giúp loại bỏ các đáp án "nghe có vẻ đúng" nhưng sai về bản chất logic.

### 4.3. Ontological Prompting (Tư duy Bản thể - Xã hội học)
Yêu cầu mô hình phân biệt giữa "Bản chất" (Essence) và "Hiện tượng" (Phenomenon):
*   **Quy tắc:** "Khi trả lời về nguồn gốc tư tưởng, phải truy nguyên về yếu tố hình thành cốt lõi (Gia đình, Văn hóa), không nhầm lẫn với các sự kiện tác động bề mặt."

---

## 5. Khả năng Agent & Công cụ (Agentic Capabilities & Tools)

Hệ thống vượt ra ngoài mô hình RAG tĩnh (Static RAG) bằng cách tích hợp khả năng "Tác tử" (Agentic), cho phép mô hình chủ động tương tác với môi trường thông qua các công cụ.

### 5.1. Cơ chế Vòng lặp Suy luận (Reasoning Loop)
Thay vì trả lời ngay lập tức, Agent thực hiện chu trình **OODA (Observe - Orient - Decide - Act)**:
1.  **Observe:** Đọc câu hỏi và ngữ cảnh ban đầu.
2.  **Orient:** Xác định xem thông tin hiện tại đã đủ để kết luận chưa?
3.  **Decide:** Nếu thiếu -> Quyết định gọi Tool. Nếu đủ -> Trả lời.
4.  **Act:** Thực thi Tool và nạp kết quả mới vào ngữ cảnh (Context Injection).

### 5.2. Kho Công cụ (Tool Inventory)

Hệ thống trang bị 2 công cụ cốt lõi cho Agent:

| Tên Tool | Chức năng (Function) | Kích hoạt khi nào? (Trigger) |
| :--- | :--- | :--- |
| **Recursive Retriever** | Truy vấn lại Database với từ khóa mới. | Khi ngữ cảnh ban đầu quá rộng hoặc không chứa thông tin cụ thể (ví dụ: thiếu "Điều khoản X" cụ thể). |
| **Python Code Executor** | Thực thi code Python trong môi trường Sandbox (Subprocess) an toàn. | Khi câu hỏi yêu cầu tính toán phức tạp, xử lý logic chuỗi, hoặc thuật toán mà LLM thuần túy thường sai sót. Code chạy với timeout 5s, hỗ trợ thư viện chuẩn (`math`, `datetime`, `re`...). |

### 5.3. Cơ chế Tự sửa lỗi (Self-Correction)
*   **Error Reflection:** Nếu Tool trả về lỗi (ví dụ: Syntax Error trong Python), Agent sẽ đọc thông báo lỗi, tự suy luận nguyên nhân và thử lại (Retry) với input đã điều chỉnh.
*   **Consistency Check:** So sánh kết quả từ Tool với kiến thức nội tại (Internal Knowledge) để đảm bảo không có sự sai lệch vô lý.

---

## 6. Quy trình Xử lý Dữ liệu (Data Pipeline)

Hệ thống đảm bảo tính toàn vẹn và có cấu trúc của dữ liệu đầu vào thông qua quy trình ETL (Extract - Transform - Load):

| Giai đoạn | Công cụ/Script | Nhiệm vụ Kỹ thuật |
| :--- | :--- | :--- |
| **Crawling** | `crawlers/*.py` | Thu thập đa nguồn (VBPL, Wiki, DVC). Xử lý Rate Limit và Retry. |
| **Cleaning & Chunking** | `process_data/*.py` | **Context-Aware Semantic Chunking:** Tách văn bản dựa trên cấu trúc ngữ nghĩa (Clause, Chapter, Subcategory) để bảo toàn ngữ cảnh cho Retrieval. |
| **History Conversion** | `scripts/convert_history.py` | Chuyển đổi PDF Lịch sử Việt Nam sang JSON phân cấp (Breadcrumbs), xử lý nhiễu Header/Footer. |
| **Indexing** | `src/indexer.py` | Tạo chỉ mục Vector + BM25. Sử dụng kiến trúc **Streaming** để xử lý dữ liệu lớn (Big Data) và cơ chế **Retry** để chịu lỗi mạng. |

---

## 7. Tài liệu & Quy trình Tái tạo Dữ liệu (Data Reproduction Guide)

Theo yêu cầu xác minh của Ban Tổ Chức, dưới đây là hướng dẫn chi tiết để chạy lại các script thu thập và xử lý dữ liệu.

### 7.1. Crawling (Thu thập Dữ liệu) - Chi tiết

Các script crawler nằm trong thư mục `crawlers/`, được chia thành các nhóm dữ liệu chính:

| Nhóm Dữ liệu | Tên Script (File) | Mô tả Chức năng | Nguồn |
| :--- | :--- | :--- | :--- |
| **Văn bản Luật (Base)** | `crawl_codes_vbpl.py` | Thu thập các Bộ luật (Code) gốc. | VBPL |
| | `crawl_laws_vbpl.py` | Thu thập các Luật (2015-nay). | VBPL |
| | `crawl_laws_vbpl_extended.py` | Thu thập Luật mở rộng (giai đoạn cũ hơn). | VBPL |
| | `crawl_legal.py` | Crawler dự phòng cho các văn bản pháp luật chung. | HthongPhapLuat |
| **Nghị định & Thông tư** | `crawl_decrees_vbpl.py` | Thu thập Nghị định (Decrees). | VBPL |
| | `crawl_vbpl_thong_tu.py` | Thu thập Thông tư hướng dẫn. | VBPL |
| | `crawl_agency55_vbpl.py` | Thu thập văn bản đặc thù cơ quan (Bộ/Ngành). | VBPL |
| | `crawl_resolutions_vbpl.py` | Thu thập Nghị quyết chung. | VBPL |
| | `crawl_resolutions.py` | Thu thập Nghị quyết chuyên đề (Sắp xếp ĐVHC). | HthongPhapLuat |
| **Nguồn Bổ sung** | `crawl_luatvietnam.py` | Crawler tổng hợp từ LuatVietnam. | LuatVietnam |
| | `crawl_decrees_luatvietnam.py` | Thu thập Nghị định từ nguồn LuatVietnam. | LuatVietnam |
| | `crawl_quyetdinh_luatvietnam.py` | Thu thập Quyết định từ LuatVietnam. | LuatVietnam |
| **Hành chính công & Data**| `crawl_dvc_procedures.py` | Lấy danh sách Thủ tục hành chính quốc gia. | DVCQG |
| | `crawl_dvc_details_stage2.py` | Lấy chi tiết từng bước thực hiện thủ tục. | DVCQG |
| | `crawl_flourish.py` | Crawl danh sách ĐVHC sau sáp nhập (2025). | Flourish |
| **Kiến thức Tổng quát** | `crawl_provinces_wiki.py` | Thông tin địa lý, hành chính 63 tỉnh thành. | Wikipedia |
| | `crawl_party_history.py` | Lịch sử Đảng và các kỳ đại hội. | Wikipedia |
| | `crawl_economics_voer.py` | Kiến thức kinh tế học cơ bản. | Voer.edu.vn |

Các script này đều hỗ trợ cơ chế Resume (tiếp tục khi ngắt quãng) và xử lý Rate Limit tự động.
Đảm bảo đã cài đặt thư viện (`pip install -r requirements.txt`).

**Ví dụ chạy Crawl Văn bản Luật (VBPL):**
```bash
# Thu thập Bộ luật
python crawlers/crawl_codes_vbpl.py

# Thu thập Luật (2015-2022)
python crawlers/crawl_laws_vbpl.py
```

**Ví dụ chạy Crawl Wikipedia (Địa lý, Lịch sử):**
```bash
# Thu thập dữ liệu Tỉnh thành
python crawlers/crawl_provinces_wiki.py
```

### 7.2. Data Processing (Xử lý & Làm sạch)
Các script nằm trong thư mục `process_data/`. Dữ liệu sau khi crawl (thường ở `data_raw/`) sẽ được chuẩn hóa thành JSONL.

**Ví dụ xử lý dữ liệu Địa lý (Sách giáo khoa & Wiki):**
```bash
python process_data/process_dialy_hsg.py
python process_data/process_provinces_data.py
```

**Ví dụ xử lý dữ liệu Lịch sử & Chính trị:**
```bash
python process_data/process_ho_chi_minh_data.py
python process_data/process_morton.py 
```

### 7.3. PDF Conversion (Chuyển đổi Tài liệu PDF) - Chi tiết

Các script trong thư mục `scripts/` chịu trách nhiệm trích xuất cấu trúc (Hierarchical Extraction) từ các nguồn sách tham khảo PDF:

| Tên Script (File) | Tài liệu Mục tiêu | Kỹ thuật Đặc biệt |
| :--- | :--- | :--- |
| `convert_history.py` | Bộ Lịch sử Việt Nam (15 Tập). | Phân cấp Chương > Bài > Mục. Loại bỏ Header/Footer rác. |
| `convert_pdf_hcm.py` | Giáo trình Tư tưởng Hồ Chí Minh. | Trích xuất mục lục tự động (Regex Pattern). |
| `convert_pdf_ktdl.py` | Giáo trình Kỹ thuật Đo lường. | **Formula Parsing:** Giữ nguyên chỉ số trên/dưới ($x^2, a_i$) để bảo toàn công thức toán học. |

**Ví dụ chuyển đổi PDF Lịch sử Việt Nam:**
```bash
python scripts/convert_history.py
# Output: data/history_vietnam_complete.json
```

**Ví dụ chuyển đổi Giáo trình Kỹ thuật Đo lường:**
```bash
python scripts/convert_pdf_ktdl.py
```

### 7.4. Indexing (Đánh chỉ mục)

Quy trình Indexing được chia làm 2 bước riêng biệt:

**Bước 1: Vector Indexing (ChromaDB)**
Lệnh này chỉ đẩy dữ liệu vào Vector DB.
```bash
python src/indexer.py --workers 8 --limit 1000
```

*Để index riêng lẻ một file (ví dụ update lại file luật mới):*
```bash
python src/indexer.py --file data/new_law.json
```

*Để xóa toàn bộ dữ liệu của một file khỏi Database:*
```bash
python src/indexer.py --delete data/wrong_file.json
```

**Bước 2: Keyword Indexing (BM25)**
Sau khi ChromaDB đã có dữ liệu, chạy lệnh này để đồng bộ và xây dựng chỉ mục từ khóa (BM25). Script sẽ tự động rà soát dữ liệu trong ChromaDB để cập nhật.
```bash
python scripts/build_bm25.py
```
*(Quá trình này có thể mất từ 15-30 phút tùy lượng dữ liệu).*

---

## 8. Cài đặt & Triển khai (Deployment)

Hệ thống được đóng gói Container hóa hoàn toàn (Dockerized), đảm bảo tính nhất quán giữa môi trường phát triển và môi trường chấm thi.

### Yêu cầu Hệ thống
*   **OS:** Linux (Ubuntu 22.04+) / Windows WSL2.
*   **CUDA:** 12.2 (Tương thích hoàn toàn với Base Image `nvidia/cuda:12.2.0`).
*   **Python:** 3.10+ (Theo Base Image Ubuntu 22.04).
*   **GPU:** Tối thiểu 4GB VRAM (Hệ thống đã tối ưu cho T4/L4). Khuyến nghị 8GB+.
*   **Disk:** ~40GB (Bao gồm Pre-indexed Database 15GB).


### 8.2. Hướng dẫn Chấm điểm (Official Submission Workflow)

Đây là quy trình từng bước để Ban Tổ Chức (BTC) chạy chấm điểm với file đề thi và API Key riêng:

**Bước 1: Tải Image**
```bash
docker pull graviton711/submission-vnpt-final:latest
```

**Bước 2: Chuẩn bị tài nguyên**
Trên máy chấm thi, đảm bảo đã có:
*   File đề thi: `/path/to/private_test.json`
*   File API Key: `/path/to/btc_keys.json` (Format JSON như BTC quy định)
*   Thư mục hứng kết quả: `/path/to/output_folder/`

**Bước 3: Chạy lệnh Chấm điểm (Full Mount)**
Chạy lệnh sau để map toàn bộ tài nguyên vào container:

```bash
docker run --gpus all --rm \
  -v /path/to/private_test.json:/data/test.json \
  -v /path/to/output_folder:/output \
  -v /path/to/btc_keys.json:/code/api_keys/api-keys.json \
  graviton711/submission-vnpt-final:latest \
  python predict.py --input /data/test.json --output /output/submission.json
```

**Ví dụ cụ thể (Concrete Example):**
Giả sử trên máy BTC có cấu trúc thư mục như sau:
*   Đề thi nằm tại: `/home/btc/data/private_test_final.json`
*   Key nằm tại: `/home/btc/keys/secret_keys.json`
*   Muốn lưu kết quả tại: `/home/btc/submission_results/`

Lệnh chạy sẽ là:
```bash
docker run --gpus all --rm \
  -v /home/btc/data/private_test_final.json:/data/test.json \
  -v /home/btc/submission_results:/output \
  -v /home/btc/keys/secret_keys.json:/code/api_keys/api-keys.json \
  graviton711/submission-vnpt-final:latest \
  python predict.py --input /data/test.json --output /output/submission.json
```

**Giải thích tham số:**
*   `-v ...:/code/api_keys/api-keys.json`: Mount file key của BTC vào đúng đường dẫn mà code mặc định đọc (`src/api.py`).
*   `/data/test.json`: Đường dẫn giả lập trong container chứa file input.
*   `/output`: Đường dẫn giả lập trong container để ghi file `submission.json` và `submission.csv`.

**Kết quả:**
Sau khi chạy xong, file `submission.csv` và `submission_time.csv` sẽ xuất hiện tại thư mục `/path/to/output_folder/` trên máy host.

---

**Cách 2: Chạy qua inference.sh (Truyền tham số theo chuẩn BTC)**

Nếu muốn sử dụng `inference.sh` làm entry-point theo đúng chuẩn Dockerfile của BTC:

```bash
docker run --gpus all --rm \
  -v /path/to/private_test.json:/code/private_test.json \
  -v /path/to/output_folder:/output \
  -v /path/to/btc_keys.json:/code/api_keys/api-keys.json \
  graviton711/submission-vnpt-final:latest \
  bash inference.sh /code/private_test.json /output/submission.json
```

**Ví dụ cụ thể:**
```bash
docker run --gpus all --rm \
  -v /home/btc/data/private_test_final.json:/code/private_test.json \
  -v /home/btc/submission_results:/output \
  -v /home/btc/keys/secret_keys.json:/code/api_keys/api-keys.json \
  graviton711/submission-vnpt-final:latest \
  bash inference.sh /code/private_test.json /output/submission.json
```

**Lưu ý:** Cách này sẽ truyền đường dẫn input/output trực tiếp vào script `inference.sh`, đảm bảo file đề thi của BTC được đọc đúng.

---

**Cách 3: Chạy tại cục bộ (Development Mode - Windows/Linux Manual)**
```bash
# 1. Cài đặt thư viện
pip install -r requirements.txt

# 2. Cấu hình API Key
# Tạo file api_keys/api-keys.json và paste key vào.

# 3. Chạy Inference
python predict.py --input public_test/test.json --output output/submission.json
```

### 8.1. Cấu hình (Configuration)
Hệ thống được cấu hình mặc định tối ưu cho môi trường Private Test (8GB VRAM, High Performance) thông qua file `src/config.py`.

Các tham số quan trọng trong `src/config.py`:
*   `MAX_RETRIES`: Số lần thử lại khi gặp lỗi API (Mặc định: 10000).
*   `USE_RERANKER`: Bật/Tắt Cross-Encoder (Mặc định: True).
*   `MAX_GPU_WORKERS`: Tự động phát hiện dựa trên VRAM khả dụng.

---

## 9. Kết luận & Chứng minh Hiệu quả

*   **Tính đúng đắn:** Việc sử dụng Hybrid Search giúp hệ thống đạt Recall@10 > 95% trên tập dữ liệu kiểm thử nội bộ (bao gồm các văn bản luật khó tìm).
*   **Tính ổn định:** Kiến trúc Singleton và cơ chế Retry giúp hệ thống chịu tải tốt, không crash khi gặp lỗi mạng.
*   **Tính tuân thủ:** Đầu ra CSV (`submission.csv`, `submission_time.csv`) được chuẩn hóa chặt chẽ theo quy định BTC.

---
*Tài liệu này xác nhận cấu trúc kỹ thuật và phương pháp luận của nhóm phát triển.*

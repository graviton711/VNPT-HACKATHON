# Nguồn gốc Dữ liệu và Bản quyền (Data Origin & Licensing)

Tài liệu này mô tả chi tiết nguồn gốc của các tập dữ liệu được sử dụng trong dự án. Thông tin nguồn gốc chi tiết (URL, metadata) được **lưu trữ trực tiếp trong từng bản ghi của các file JSON/JSONL**.

## 1. Dữ liệu Kiến thức Bách khoa (Wikipedia)
Các tập dữ liệu sau được trích xuất từ **Wikipedia Tiếng Việt (vi.wikipedia.org)**, tuân thủ giấy phép **CC BY-SA 4.0**:

**Các tệp tin:**
*   `academic_biology.jsonl`
*   `academic_chemistry.jsonl`
*   `academic_computer_science.jsonl`
*   `academic_economics.jsonl`

*   `academic_maths.jsonl`
*   `academic_philosophy.jsonl`
*   `academic_physics.jsonl`
*   `medical_knowledge.jsonl` (Y học thường thức)
*   `dialy_hsg.json` (Địa lý học sinh giỏi)
*   `general_characters.jsonl` (Nhân vật)
*   `general_skills.jsonl` (Kỹ năng)
*   `general_special.jsonl` (Kiến thức chung)
*   `dictionary_combined.jsonl` (Từ điển)
*   `culture_vietnam.jsonl` (Văn hóa Việt Nam)
*   `provinces_wiki_chunked.json` (Thông tin tỉnh thành)
*   `history_hochiminh_bio.jsonl` (Tiểu sử Hồ Chí Minh - Wiki)
*   `knowledge_wikipedia.jsonl`

**Giấy phép:**
- Creative Commons Attribution-ShareAlike 4.0 International.

## 2. Dữ liệu Lịch sử & Tư tưởng (Sách & Giáo trình)

**Các tệp tin:**
*   `ban_an_che_do_thuc_dan_phap_chunked.json`
    - **Nguồn:** `sachne.com`
    - **Tác phẩm:** Bản án chế độ thực dân Pháp (Nguyễn Ái Quốc).
*   `giao_trinh_hcm_structured.json`
    - **Nguồn:** Giáo trình Bộ Giáo dục & Đào tạo (`sachne.com`).
*   `gt_lich_su_dang_chunked.json`
    - **Nguồn:** Giáo trình Lịch sử Đảng Cộng sản Việt Nam.
*   `politics_ideology.jsonl`
    - **Nguồn:** Tổng hợp từ các tài liệu chính trị, tư tưởng (đã ghi nguồn trong file).

## 3. Dữ liệu Văn bản Quy phạm Pháp luật (Legal Documents)

Dữ liệu được thu thập từ **Cơ sở dữ liệu Quốc gia về Văn bản Pháp luật (`vbpl.vn`)** và **LuatVietnam (`luatvietnam.vn`)**.

**Các tệp tin từ VBPL:**
*   `codes_vbpl.json` (Bộ luật)
*   `laws_vbpl_2015_2022.json`
*   `laws_vbpl_2023_2025.json`
*   `laws_vbpl_thong_tu.json`
*   `resolutions_vbpl_2023_2025.json`
*   `vbpl_cqbh_55.json`
*   `mergers_2025.json`
*   `mergers_2025_nghiquyet.json`

**Các tệp tin từ LuatVietnam & Khác:**
*   `decrees_corpus_cleaned.json` (Các Nghị định - Nguồn LuatVietnam/VBPL)
*   `quyetdinh_corpus.json` (Quyết định)
*   `dvc_procedures_full.json` (Thủ tục hành chính - `dichvucong.gov.vn`)

## 4. Dữ liệu Văn hóa & Tôn giáo

**Các tệp tin:**
*   `culture_chonthieng.json`
    - **Nguồn:** `chonthieng.com` (Đã xác nhận quyền sử dụng phi thương mại).
*   `phat_hoc_pho_thong.jsonl`
    - **Nguồn:** Tài liệu Phật học phổ thông (Public Domain).
*   `cadao_danca.json`
    - **Nguồn:** *Đang cập nhật nguồn cụ thể*. (Nguồn văn học dân gian).
*   `thanhngu.json`
    - **Nguồn:** Tục ngữ, thành ngữ Việt Nam (Văn học dân gian).

## 5. Dữ liệu Sách Kinh tế & Kỹ thuật (Textbooks)

**Các tệp tin:**
*   `economics_micro_chunked.json` / `economics_macro_chunked.json`
*   `macroeconomics.jsonl` / `microeconomics.jsonl`
*   `finance_general.jsonl`
*   `nguyenliketoan.json`
*   `ky_thuat_do_luong_structured.json`
    - **Nguồn:** `https://cuuduongthancong.com/` (Cửu Dương Thần Công).

## 6. Sách Tham khảo Nước ngoài (Translated)

**Các tệp tin:**
*   `morton_extracted_chunks.json` / `morton_strucutred_translated.json` (Về lịch sử chính trị Mỹ)
    - **Nguồn:** `https://zlib.pub/book/americas-three-regimes-a-new-political-history-6rg4jejc6e60` (Sách tham khảo).
*   `stallings_translated.json` (Về hệ điều hành máy tính)
    - **Nguồn:** `https://drive.google.com/file/d/0B5tR1YhNBlD2dlZXUGRBY1RYRTg/view?resourcekey=0-prIVHwW9nBabHi42-ma5Nw` (Sách dịch/tham khảo).

---
**Lưu ý:**
Chi tiết về đường dẫn gốc (URL) và metadata của từng đoạn văn bản được lưu trữ trong trường `source`, `url`, hoặc `metadata` của từng đối tượng JSON trong các file dữ liệu.

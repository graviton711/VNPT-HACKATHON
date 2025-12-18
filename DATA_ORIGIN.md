# Nguồn gốc Dữ liệu và Bản quyền (Data Origin & Licensing)

Tài liệu này mô tả chi tiết nguồn gốc của các tập dữ liệu được sử dụng trong dự án, đồng thời làm rõ tính hợp pháp và giấy phép sử dụng (Open Source / Public Domain) cho mục đích nghiên cứu và phát triển.

## 1. Tổng hợp Dữ liệu Kiến thức & Học thuật (General Knowledge & Academic Data)

**Các tệp tin hiện có:**
*   `academic_biology.jsonl`
*   `academic_chemistry.jsonl`
*   `academic_computer_science.jsonl`
*   `academic_economics.jsonl`
*   `academic_geography.jsonl`
*   `academic_maths.jsonl`
*   `academic_philosophy.jsonl`
*   `academic_physics.jsonl`
*   `culture_vietnam.jsonl`
*   `economics_macro.json`
*   `finance_general.jsonl`
*   `general_characters.jsonl`
*   `general_skills.jsonl`
*   `general_special.jsonl`
*   `history_hochiminh_bio.jsonl`
*   `history_hochiminh_collected.json`
*   `history_party.json`
*   `knowledge_wikipedia.jsonl`
*   `medical_knowledge.jsonl`
*   `politics_ideology.jsonl`

**Nguồn gốc Dữ liệu:**
- **Wikipedia Tiếng Việt** (`vi.wikipedia.org`)
- Dữ liệu được trích xuất và tổng hợp từ các bài viết công khai trên bách khoa toàn thư mở Wikipedia.

**Giấy phép & Quyền sử dụng (Licensing):**
- **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0):**
    - Toàn bộ nội dung văn bản trên Wikipedia được phát hành dưới giấy phép này.
    - **Quyền hạn:** Cho phép sao chép, phân phối, và sửa đổi nội dung, kể cả cho mục đích thương mại, miễn là tuân thủ các điều kiện ghi công (Attribution) và chia sẻ tương tự (ShareAlike).
    - **Tuân thủ:** Dự án sử dụng dữ liệu này cho mục đích nghiên cứu và huấn luyện mô hình AI, tuân thủ yêu cầu ghi rõ nguồn gốc từ Wikipedia.

## 2. Dữ liệu Giáo trình Lịch sử Đảng (Party History Textbook)
**Các tệp tin:**
- `history_party_voer.json`

## 3. Dữ liệu Kinh tế học (Economics)
**Các tệp tin:**
- `economics_micro_voer.json` (Kinh tế vi mô, Quản trị chiến lược)

## 4. Dữ liệu Văn bản Quy phạm Pháp luật (Legal Documents)
**Các tệp tin:**
- `laws_vbpl_2023_2025.json` (Luật 2023-2025)
- `codes_vbpl.json` (Bộ luật - Toàn bộ)
- `resolutions_vbpl_2023_2025.json` (Nghị quyết 2023-2025)
- `decrees_vbpl_2023_2025.json` (Nghị định 2023-2025)

**Nguồn gốc (chung cho mục 2, 3, 4):**
- **Thư viện Học liệu Mở Việt Nam (VOER)** (`voer.edu.vn`) - *Cho mục 2 và 3*
- **Cơ sở dữ liệu Quốc gia về Văn bản Pháp luật (VBPL)** (`vbpl.vn`) - *Cho mục 4*

## 6. Dữ liệu Hồ Chí Minh & Đào tạo (Ho Chi Minh Ideology & Education)
**Các tệp tin:**
- `ban_an_che_do_thuc_dan_phap.json`
- `giao_trinh_tu_tuong_ho_chi_minh.json`

**Nguồn gốc & Bản quyền:**
- **Bản án chế độ thực dân Pháp**:
    - Tác giả: Nguyễn Ái Quốc.
    - Nguồn tải: `sachne.com`.
    - Minh chứng bản quyền: **Public Domain (Phạm vi công cộng)**. Tác phẩm xuất bản lần đầu năm 1925, đã hết thời hạn bảo hộ bản quyền.
- **Giáo trình Tư tưởng Hồ Chí Minh**:
    - Tác giả: Bộ Giáo dục và Đào tạo.
    - Nguồn tải: `sachne.com`.
    - Minh chứng bản quyền: Sử dụng cho mục đích giáo dục và nghiên cứu phi thương mại (Educational Use).

**Giấy phép & Quyền sử dụng:**
- **Creative Commons Attribution 3.0 (CC BY 3.0):**
    - Nội dung trên VOER được phát hành dưới giấy phép này (trừ khi có ghi chú khác).
    - **Quyền hạn:** Cho phép chia sẻ và chỉnh sửa miễn là ghi công tác giả.
    - **Tuân thủ:** Đã ghi rõ nguồn gốc từ VOER và giữ nguyên thông tin bản quyền trong metadata.

## 7. Dữ liệu Văn hóa - Chốn Thiêng (Spiritual Culture Data)
**Các tệp tin:**
- `culture_chonthieng.json`

**Nguồn gốc & Bản quyền:**
- **Nguồn dữ liệu**: Website Chốn Thiêng (chonthieng.com).
- **Xác nhận quyền sử dụng**:
    - **Trạng thái**: Đã được sự xác nhận và đồng ý từ Quản trị viên (Admin) website.
    - **Phạm vi sử dụng**: Được phép sử dụng toàn bộ thông tin công khai để phục vụ cộng đồng và huấn luyện AI (phi thương mại).
    - **Yêu cầu**: Trích dẫn nguồn (Attribution).
- **Minh chứng**: [Confirmed Support Message](docs/licenses/chonthieng_permission.png) (Lưu trữ nội bộ).

## 8. Dữ liệu Giáo trình Kinh tế Bổ sung (Supplementary Economics Textbooks)
**Các tệp tin:**
- `economics_micro.json` / `economics_micro_chunked.json` (Giáo trình Kinh tế Vi mô)
- `economics_macro.json` / `economics_macro_chunked.json` (Giáo trình Kinh tế Vĩ mô)

**Nguồn gốc & Bản quyền:**
- **Nguồn tải**: `tailieuvui.com`.
- **Mục đích sử dụng**: Sử dụng cho mục đích giáo dục, nghiên cứu phi thương mại (Educational/Fair Use).


## 9. Dữ liệu Tỉnh thành Việt Nam (Vietnam Provinces)
**Các tệp tin:**
- `provinces_wiki.json` / `provinces_wiki_chunked.json`

**Nguồn gốc & Bản quyền:**
- **Wikipedia Tiếng Việt** (`vi.wikipedia.org`).
- **Giấy phép**: CC BY-SA 4.0.

---
**Tổng kết:**
Dữ liệu trong thư mục `data/` được tổng hợp từ các nguồn uy tín và tuân thủ bản quyền: Wikipedia Tiếng Việt (CC BY-SA 4.0), VOER (CC BY 3.0), VBPL (Dữ liệu công), Sách Nè/Tài Liệu Vui (Educational Use), và Chốn Thiêng (Được cấp phép sử dụng phi thương mại). Tất cả đều đảm bảo tính pháp lý cho mục đích nghiên cứu và phát triển.


Morton Keller: https://zlib.pub/download/americas-three-regimes-a-new-political-history-6rg4jejc6e60?hash=23ba14d8c54e16769ada7383798a1d44

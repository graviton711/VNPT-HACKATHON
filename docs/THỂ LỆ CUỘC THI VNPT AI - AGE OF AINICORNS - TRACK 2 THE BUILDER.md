# THỂ LỆ CUỘC THI VNPT AI - AGE OF AINICORNS - TRACK 2 THE BUILDER

## 1. Đối tượng dự thi

*   **Cá nhân hoặc tổ chức** đều có thể đăng ký tham gia.
*   Đội thi phải có ít nhất một thành viên đang sinh sống, học tập hoặc làm việc tại Việt Nam.
*   Tất cả thành viên đều phải từ **đủ 18 tuổi trở lên**, không phân biệt quốc tịch.
*   Người tham gia có thể tham gia theo cá nhân hoặc theo nhóm tối đa **5 thành viên**.
*   Mỗi đội cần có một trưởng nhóm đại diện liên hệ chính thức.
*   Mỗi cá nhân chỉ được tham gia **một đội duy nhất** và không được thay đổi thành viên sau khi Ban tổ chức xác nhận đăng ký.

## 2. Thể lệ cuộc thi

Cá nhân/đội thi tập trung vào việc làm cho một mô hình LLM hoạt động tốt hơn. Nhiệm vụ là tinh chỉnh, tối ưu hoặc tái cấu trúc pipeline sử dụng mô hình để đạt được hiệu suất vượt trội khi trả lời một bộ câu hỏi trắc nghiệm được thiết kế sát với thực tiễn sử dụng của người Việt.

Đây không chỉ là bài kiểm tra khả năng xử lý ngôn ngữ tự nhiên, mà còn là thước đo cho mức độ hiểu biết văn hoá, tư duy logic và độ tin cậy khi triển khai trong môi trường Việt Nam.

### 2.1. API được cung cấp

Các đội sẽ được cung cấp API từ mô hình của VNPT AI với Quota như sau:

| Mô hình | Quota |
| :--- | :--- |
| `vnptai_hackathon_small` | 1000 api requests/ngày |
| `vnptai_hackathon_large` | 500 api requests/ngày |
| `vnptai_hackathon_embedding` | 500 api requests/ngày |

### 2.2. Bộ dữ liệu

Bộ dữ liệu được thiết kế xoay quanh các kiến thức chính xác, chính thống liên quan đến văn hoá, lịch sử, địa lý, chính trị Việt Nam, với các nhóm:

*   Câu hỏi bắt buộc không được trả lời
*   Câu hỏi bắt buộc phải trả lời đúng
*   Câu hỏi đọc hiểu văn bản dài
*   Câu hỏi toán học và tư duy logic
*   Câu hỏi đa lĩnh vực

### 2.3. Phạm vi cho phép

*   **Thu thập dữ liệu**: Các đội được phép thu thập dữ liệu trên internet để xây dựng vector database, yêu cầu các đội thu thập dữ liệu từ các nguồn mở, license cho phép sử dụng. BTC sẽ không chịu trách nhiệm nếu các đội thi sử dụng các dữ liệu bảo mật hoặc không được cấp phép/license.
*   **External API**: Pipeline **không được sử dụng** các external API như ChatGPT, Gemini,... hay API cung cấp các thông tin search, tra cứu dưới bất kỳ hình thức nào trong thời gian inference.

## 3. VÒNG 1: TEST THE LIMIT

### 3.1. Nhiệm vụ

*   **Thời gian**: **05/12/2025** tới hết ngày **17/12/2025**.
*   Các đội thi sẽ được cấp quota truy cập API giới hạn mỗi ngày, và làm việc với bộ dữ liệu public test để điều chỉnh, đánh giá mô hình và thực thi các chiến lược để tối ưu model.

### 3.2. Tập dữ liệu

*   **Dev set**: 100 câu hỏi
*   **Test set (public)**: 400 câu hỏi

### 3.3. Quota sử dụng trong Vòng 1

| Mô hình | Quota |
| :--- | :--- |
| `vnptai_hackathon_small` | 1000 api requests/ngày |
| `vnptai_hackathon_large` | 500 api requests/ngày |
| `vnptai_hackathon_embedding` | 500 api requests/phút |

*   **Số lần submit kết quả**: Tối đa **5 lần/ngày**.

### 3.4. Yêu cầu đầu ra

*   **Docker Container**: Đẩy lên Docker Hub.
*   **Entry-point**: Đọc `public_test.csv` hoặc `private_test.csv` tại `/data`, ghi `pred.csv` vào `/output` với hai cột: `qid`, `answer` (A/B/C/D).
*   **Github**: Chứa code và các bước chạy reproduce kết quả trong container.
*   **Tài liệu thuyết minh phương pháp**: Định dạng tuỳ chọn với mục tiêu thể hiện được rõ nhất tính sáng tạo, hiệu quả của chiến lược tối ưu mô hình đã lựa chọn.

### 3.5. Kết quả

*   Các cá nhân/đội thi xem trực tiếp kết quả trên leaderboard.
*   Trong vòng **72h** kể từ khi kết thúc vòng 1, các cá nhân/đội thi phải gửi đầy đủ tài liệu được BTC yêu cầu trong mục “Yêu cầu đầu ra”. Các đội thi không gửi lại theo thời hạn sẽ tự động bị loại khỏi cuộc thi.

## 4. VÒNG 2: BEYOUND THE LIMIT

### 4.1. Nhiệm vụ

Đội thi nộp phiên bản Docker cuối cùng đã được tinh chỉnh và sẵn sàng kiểm chứng. BTC sẽ thực hiện đánh giá trên bộ **private test gồm 2000 câu hỏi**, với các tiêu chí:

*   Độ chính xác (Accuracy)
*   Thời gian inference (Time-to-first-token & Req/s)
*   Tư duy tối ưu & sáng tạo

### 4.2. Kết quả

Sau **7 ngày** kể từ khi các đội thi hoàn thiện nộp tài liệu được yêu cầu ở Vòng 1, BTC công bố danh sách **5 cá nhân/đội thi** có cơ hội giành giải.

## 5. ĐÊM CHUNG KẾT

*   **Thời gian**: Diễn ra ngày **25/12/2025**.
*   **Nội dung**: Công bố leaderboard Top 3. Các đội lần lượt trình bày (thời lượng 5 phút) tổng quan giải pháp (logic xử lý), hướng phát triển trong tương lai.

# Task - StockInsight

Cập nhật: 09/10/2026. `[x]` đã hoàn thành; `[ ]` chưa hoàn thành. Các mục sau bước khởi tạo là kế hoạch phát triển, chưa được thực hiện trong yêu cầu này.

## 0. Khởi tạo - phạm vi yêu cầu hiện tại

- [x] Đọc toàn bộ đề PDF một trang và bản hướng triển khai người dùng cung cấp.
- [x] Phân biệt yêu cầu đề gốc với đề xuất kỹ thuật.
- [x] Tạo cây thư mục dự án trong `gk/`.
- [x] Tạo `projectcontext.md` và `task.md`.
- [x] Tạo README, cấu hình ban đầu, mô-đun khung và tài liệu định hướng.
- [x] Lưu bản sao tài liệu đầu vào trong `docs/references/`.

## 1. P0 - Dữ liệu và hợp đồng đầu vào/đầu ra

- [ ] Chọn một mã đầu tiên và phạm vi ngành hỗ trợ.
- [ ] Kiểm tra nguồn thật cho giá, tài chính và thông tin doanh nghiệp; thử một mã/một kỳ trước khi tích hợp repository tham khảo.
- [ ] Lưu dữ liệu gốc trong `data/raw/` và đăng ký nguồn trong `data/metadata/source_registry.csv`.
- [ ] Xác định đơn vị, cơ sở giá, kỳ, phạm vi báo cáo và thời điểm công bố/thu thập.
- [ ] Định nghĩa AnalysisRequest, dữ liệu chuẩn, ValidationResult và AnalysisResult trong `src/models.py`.
- [ ] Viết bộ đọc file trong `src/data/loaders.py`, bộ kết nối nguồn trong `providers.py`.
- [ ] Chuẩn hóa và kiểm tra trong `normalize.py`/`validate.py`; lọc dữ liệu theo ngày phân tích.

**Điều kiện hoàn thành:** dữ liệu một mã đọc được, truy vết về nguồn được, dữ liệu sai/thiếu có thông báo; hợp đồng kết quả thống nhất cho UI/PDF.

## 2. P0 - Luồng phân tích và PDF tối thiểu

- [ ] Điều phối bằng `src/pipeline.py`: yêu cầu -> đọc -> chuẩn hóa -> kiểm tra -> phân tích -> lưu kết quả.
- [ ] Tính chỉ tiêu tối thiểu đủ dữ liệu và tạo nhận định có căn cứ.
- [ ] Bổ sung font Unicode thật trong `assets/fonts/`, kiểm tra quyền phân phối.
- [ ] Tạo biểu đồ, bảng và PDF tiếng Việt từ cùng AnalysisResult.
- [ ] Lưu request.json, validation.json, analysis.json, figures và report.pdf theo từng lần chạy.
- [ ] Tạo giao diện Streamlit: mã, ngày phân tích, chạy phân tích, xem kết quả và tải PDF.
- [ ] Chốt/cài phiên bản thư viện đã kiểm chứng và cập nhật hướng dẫn chạy.

**Điều kiện hoàn thành:** chạy xuyên suốt một mã bằng dữ liệu thật có nguồn và mở được PDF; số liệu màn hình và báo cáo khớp.

## 3. P1 - Phân tích đầy đủ và tùy chọn

- [ ] Tổng quan doanh nghiệp: mã, tên, ngành, hoạt động, ngày giá và kỳ tài chính.
- [ ] Giá: lợi suất, khối lượng, MA20/MA50 khi đủ phiên, mức sụt giảm lớn nhất.
- [ ] Tài chính theo ngành: tăng trưởng cùng kỳ, biên lợi nhuận, ROE, nợ vay/vốn chủ, CFO và chất lượng lợi nhuận khi phù hợp.
- [ ] Kiểm soát quý lũy kế, quý độc lập và TTM; thống nhất EPS và phạm vi số liệu.
- [ ] P/E/P/B khi đủ điều kiện; nêu rõ cơ sở so sánh và giả định.
- [ ] Tin tức có ngày/nguồn và nhận định về cơ hội, rủi ro, điều kiện theo dõi.
- [ ] Cho chọn giai đoạn, độ dài và phần báo cáo; PDF phản ánh đúng lựa chọn.
- [ ] Hiển thị trạng thái đủ/thiếu/lỗi dữ liệu và phạm vi mã/ngành hỗ trợ.
- [ ] Truy vết từng chỉ tiêu về nguồn, kỳ, đơn vị và công thức.

**Điều kiện hoàn thành:** nhận định phù hợp doanh nghiệp, không dùng công thức sai ngành và không tạo kết quả khi dữ liệu không đủ điều kiện.

## 4. P1 - Kiểm chứng và hoàn thiện

- [ ] Đối chiếu giá và chỉ tiêu tài chính trọng yếu với tài liệu gốc; lưu bằng chứng.
- [ ] Kiểm tra đổi đơn vị nghìn/triệu/tỷ đồng và cơ sở giá.
- [ ] Kiểm tra lũy kế/TTM, không trộn hợp nhất/riêng lẻ, không dùng dữ liệu công bố sau ngày phân tích.
- [ ] Kiểm tra thiếu dữ liệu, mẫu số 0, lợi nhuận âm và kỳ so sánh không phù hợp.
- [ ] Thử ít nhất hai mã bổ sung; kết quả thay đổi đúng dữ liệu của mã.
- [ ] Thay đổi giả định định giá và xác nhận kết quả cập nhật.
- [ ] Bỏ một phần báo cáo, kiểm tra PDF bỏ đúng phần đó; đối chiếu UI với PDF.
- [ ] Render và xem toàn bộ PDF: font tiếng Việt, bảng, biểu đồ, nguồn, số trang, không tràn/cắt chữ.
- [ ] Thêm test cho các lỗi tính toán/dữ liệu quan trọng, không tạo test chỉ để kiểm tra file khung.
- [ ] Chạy lại theo README với môi trường sạch khi khả thi.

**Điều kiện hoàn thành:** có bằng chứng kiểm chứng, các lỗi dữ liệu trọng yếu được xử lý và PDF đọc tốt.

## 5. P1 - Tài liệu và bộ nộp

- [ ] Hoàn thiện README: cài đặt, lệnh chạy, dữ liệu, phạm vi hỗ trợ.
- [ ] Hoàn thiện architecture.md, methodology.md, data_dictionary.md và demo_script.md.
- [ ] Chuẩn bị dữ liệu mẫu có nguồn và PDF mẫu thật trong `submission/`.
- [ ] Chuẩn bị thuyết trình/video demo nếu hình thức nộp yêu cầu hoặc cho phép.
- [ ] Bổ sung thông tin nhóm, rà soát bộ nộp theo yêu cầu giảng viên.

**Điều kiện hoàn thành:** người khác có thể chạy lại và hiểu nguồn, phương pháp, giới hạn. Hạn ghi trong đề: 11:30 ngày 09/10/2026.

## 6. P2 - Mở rộng sau MVP

- [ ] Ba kịch bản định giá và kiểm tra độ nhạy.
- [ ] DCF khi đủ dữ liệu/giả định phù hợp.
- [ ] AI hỗ trợ diễn đạt từ kết quả đã tính và có nguồn, nếu cần.
- [ ] Parquet, bộ đệm và tích hợp nguồn bổ sung khi có nhu cầu.

## Bước tiếp theo

Chốt hợp đồng dữ liệu, đối chiếu giá HPG và cơ sở điều chỉnh với nguồn thứ hai, trích xuất/kiểm tra chỉ tiêu tài chính từ PDF rồi xây luồng phân tích/PDF. Tiến độ thử nghiệm bên dưới chỉ xác nhận khả năng thu thập dữ liệu.

## Tiến độ bổ sung: kiểm thử HPG

- [x] Chọn HPG làm mã thử đầu tiên theo yêu cầu người dùng.
- [x] Viết CLI tự lấy giá ngày, loại phiên hiện tại theo UTC+7.
- [x] Lưu JSON nguồn, CSV giá, ngày lấy dữ liệu và đăng ký nguồn.
- [x] Lấy 261 bản ghi ngày từ 09/10/2025 đến 08/10/2026; kiểm tra cấu trúc không có lỗi.
- [x] Tự tìm/tải hai BCTC hợp nhất HPG có ngày công bố phù hợp; kiểm tra PDF mở được.
- [x] Chạy 5 kiểm thử offline về thời gian, metadata và dữ liệu lỗi.
- [ ] Đối chiếu giá và cơ sở điều chỉnh với nguồn độc lập.
- [ ] Trích xuất số liệu tài chính, xác minh đơn vị/kỳ và đối chiếu PDF.
- [ ] Thu thập thông tin doanh nghiệp và tin tức theo schema.
- [ ] Bổ sung lịch sử báo cáo từ các trang tiếp theo và quy tắc chọn phiên bản soát xét/kiểm toán.
- [ ] Hoàn thiện AnalysisResult, phân tích và PDF đầu ra.

Đề xuất tần suất bản đầu: dữ liệu cuối ngày, lấy tự động khi chạy; chưa chạy nền/realtime. Các mục P0/P1 bên trên giữ trạng thái chưa hoàn thành nếu mới chỉ đạt một phần.

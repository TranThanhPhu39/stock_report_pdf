# StockInsight

Khung dự án phân tích cơ hội đầu tư cổ phiếu Việt Nam và tự động xuất PDF theo lựa chọn người dùng.

## Trạng thái

Đã tạo cấu trúc, cấu hình và tài liệu. Các mô-đun Python chỉ mô tả trách nhiệm; chưa có ứng dụng phân tích hoàn chỉnh, dữ liệu thị trường hay PDF mẫu.

Đọc `projectcontext.md` để hiểu yêu cầu/kiến trúc và `task.md` để theo dõi tiến độ. Đề gốc và bản đề xuất nằm trong `docs/references/`.

## Thư mục

- `config/`: cài đặt, quy tắc, giả định định giá.
- `src/data/`: mã đọc nguồn, chuẩn hóa, kiểm tra.
- `src/analysis/`: tính chỉ tiêu, tạo nhận định.
- `src/reporting/`: biểu đồ, xuất PDF.
- `assets/fonts/`: font Unicode sẽ được bổ sung.
- `data/`: dữ liệu gốc, dữ liệu chuẩn, danh mục nguồn.
- `outputs/runs/`: kết quả từng lần chạy.
- `tests/fixtures/`: dữ liệu kiểm thử sẽ được bổ sung.
- `docs/`: kiến trúc, phương pháp, từ điển dữ liệu, demo.
- `submission/`: bộ nộp thực tế sau khi hoàn thiện.

## Công nghệ dự kiến

Python + Streamlit + pandas/numpy + matplotlib + ReportLab + PyYAML. `requirements.txt` chưa chốt phiên bản hoặc cài đặt.

Sau khi triển khai P0, lệnh chạy dự kiến: `python -m streamlit run app.py`. Hiện chưa có ứng dụng phân tích để chạy.

Bước tiếp theo: dữ liệu một mã có nguồn, phạm vi ngành và hợp đồng dữ liệu.

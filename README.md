# StockInsight

Khung dự án phân tích cơ hội đầu tư cổ phiếu Việt Nam và tự động xuất PDF theo lựa chọn người dùng.

## Trạng thái

Đã có bộ lấy giá ngày tự động và tải BCTC hợp nhất HPG. Đã thử nguồn thật cho HPG và chạy 5 kiểm thử offline. Các mô-đun phân tích/giao diện/PDF còn là khung, chưa có báo cáo phân tích hoàn chỉnh. Giá chưa đối chiếu độc lập; chỉ tiêu tài chính chưa trích xuất.

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

## Tự lấy dữ liệu HPG

Cài dependency cho bộ lấy dữ liệu: `python -m pip install beautifulsoup4`.

```powershell
python -m scripts.fetch_data --ticker HPG --start 2025-10-09 --as-of 2026-10-09
python -m unittest discover -s tests -v
```

Giá được lưu trong `data/processed/`, dữ liệu gốc trong `data/raw/`; log và trạng thái trong `outputs/runs/<run_id>/`. Lỗi từng nguồn được lưu và CLI trả mã lỗi khác 0 nếu có lỗi. Các nguồn công khai có thể thay đổi, chặn hoặc giới hạn truy cập.

Chế độ bản đầu đề xuất: cuối ngày, luôn loại ngày hiện tại theo UTC+7 để tránh phiên chưa hoàn tất. Không có cập nhật nền/realtime. Không dùng cơ sở giá chưa xác minh để khẳng định lợi suất điều chỉnh hay giá mục tiêu. PDF tài chính tải từ nguồn công bố chưa được chuyển thành chỉ tiêu. Bộ tìm báo cáo hiện chỉ hỗ trợ HPG và trang danh sách đầu tiên.

Xem `docs/hpg_data_check.md` để biết kết quả thử nguồn thật và phần cần hoàn thiện.

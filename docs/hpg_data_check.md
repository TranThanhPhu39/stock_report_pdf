# Kiểm thử tự lấy dữ liệu HPG

Ngày kiểm tra: 09/10/2026, UTC+7.

Lệnh: `python -m scripts.fetch_data --ticker HPG --start 2025-10-09 --as-of 2026-10-09`.

Lượt chạy: `HPG_20261009_105621_805649`. Trạng thái thu thập: thành công, không có lỗi nguồn trong lượt này.

| Thành phần | Kết quả |
|---|---|
| Giá Yahoo Finance HPG.VN | 261 bản ghi ngày, 09/10/2025 đến 08/10/2026 |
| Kiểm tra giá | Đúng mã/đơn vị từ metadata; ngày, trùng ngày, OHLC và khối lượng hợp lệ |
| BCTC hợp nhất soát xét 6 tháng 2026 | Tải thành công, công bố 28/08/2026, PDF 67 trang |
| BCTC hợp nhất quý II/2026 | Tải thành công, công bố 30/07/2026, PDF 37 trang |
| Kiểm thử offline | 5 kiểm thử đạt |

## Bằng chứng tại workspace

- `data/processed/HPG_20261009_105621_805649_prices.csv`: giá chuẩn hóa đơn vị từ metadata, chưa xác minh cơ sở điều chỉnh.
- `data/raw/prices/HPG_20261009_105621_805649.json`: phản hồi nguồn nguyên trạng.
- `data/raw/documents/HPG_20261009_105621_805649_listing.html`: danh sách công bố đã tải.
- `data/raw/documents/`: hai PDF gốc; SHA-256 được ghi trong log.
- `outputs/runs/HPG_20261009_105621_805649/`: request, validation, acquisition, sources và danh sách PDF ứng viên.
- `data/metadata/source_registry.csv`: nguồn và thời điểm thu thập.

Nguồn giá thử nghiệm: `https://query1.finance.yahoo.com/v8/finance/chart/HPG.VN` với tham số khoảng ngày/interval=1d. Nguồn công bố: https://www.hoaphat.com.vn/quan-he-co-dong/bao-cao-tai-chinh.

## Phương án cuối ngày

Ứng dụng nên tự lấy dữ liệu khi chạy, dùng phiên hoàn tất gần nhất để số liệu báo cáo tái tạo được. Tài chính dùng kỳ đã công bố, tin tức dùng thời điểm công bố; tần suất của ba nhóm dữ liệu khác nhau.

Hiện bộ lấy giá chỉ nhận ngày trước ngày hiện tại theo UTC+7, kể cả sau giờ đóng cửa. Đây là quy tắc thận trọng, không khẳng định nguồn đã chốt phiên hôm nay. Tương lai có thể bổ sung lịch giao dịch và trạng thái nguồn để nhận phiên hôm nay sau khi hoàn tất.

## Giới hạn và bước tiếp theo

- 261 là số bản ghi nguồn trả về, chưa đối chiếu số phiên với lịch giao dịch HOSE.
- Giá chưa đối chiếu nguồn thứ hai, cơ sở điều chỉnh Yahoo OHLC chưa xác minh; không khẳng định lợi suất điều chỉnh/tổng lợi suất.
- PDF mở được không chứng minh số liệu đã trích xuất đúng. Chưa trích xuất chỉ tiêu tài chính hoặc xử lý OCR.
- Hai báo cáo có kỳ chồng lấp; cần chọn phiên bản phù hợp và không cộng trùng khi tính TTM.
- Chưa tự lấy tin tức, chưa có phân tích/định giá hoặc PDF phân tích đầu ra.
- Nguồn giá nhận mã làm tham số nhưng chưa kiểm chứng mã khác. Bộ tìm báo cáo chỉ hỗ trợ HPG, trang danh sách đầu tiên.
- Không có API key trong mã; không có lịch chạy nền hoặc cam kết realtime. Khả năng truy cập nguồn công khai có thể thay đổi.

Tiếp theo: đối chiếu giá/sự kiện vốn, mở rộng lịch sử tài chính, trích xuất/kiểm tra chỉ tiêu và kết nối pipeline phân tích.

# Rà soát code và nhu cầu nhà đầu tư — 13/10/2026

## Kết luận

StockInsight phù hợp để nghiên cứu ban đầu một cổ phiếu Việt Nam và tạo báo cáo có nguồn. Chưa đáp ứng đầy đủ nhu cầu của nhà đầu tư dùng hằng ngày để chọn cổ phiếu, phân bổ vốn và theo dõi danh mục. Đánh giá dựa trên code, tài liệu dự án, kiểm thử và luồng giao diện với kết quả MBB đã lưu; không phải kiểm chứng lại dữ liệu trực tiếp của toàn thị trường hay đánh giá bố cục bằng ảnh chụp trình duyệt.

## Lỗi đã sửa

- `src/analysis/recommendation.py`: trạng thái đối chiếu tổng hợp có thể thuộc năm cũ nhưng vẫn nâng độ tin cậy của tài chính năm đang định giá. Nay cần có kiểm tra khớp thuộc đúng năm/ngày cuối kỳ đang sử dụng để đủ điều kiện tích lũy.
- `src/data/normalize.py`: tháng bắt đầu `00` có thể vượt qua phép đếm 12 tháng (ví dụ `202500–202511`). Nay kiểm tra cả tháng đầu và cuối.
- `src/data/normalize.py`, `src/analysis/financial.py`: dòng chỉ tiêu trùng có thể ghi đè số liệu mâu thuẫn, làm kết quả phụ thuộc thứ tự đầu vào. Nay từ chối dữ liệu mâu thuẫn; khi gộp các bảng, giá trị null không ghi đè giá trị đã có.
- `app.py`: hộp tình trạng dữ liệu chỉ gom cảnh báo acquisition, bỏ sót cảnh báo chất lượng từ các bước nghiên cứu/tài chính. Nay gom và loại trùng cảnh báo từ cả hai nơi; trước đây các cảnh báo quality vẫn có ở tab nguồn dữ liệu.
- Bổ sung kiểm tra phòng vệ số cổ phiếu và giá đóng cửa dương, hữu hạn trước khi tính định giá chính.

## Kiểm chứng

- Trước sửa: 202 kiểm thử đạt. Sau sửa: 210 kiểm thử đạt, gồm hồi quy cho các lỗi trên.
- Streamlit AppTest: màn hình đầu, thao tác phân tích, 8 tab, cảnh báo chất lượng và nút tải PDF hoạt động. Dùng kết quả MBB đã lưu và PDF có sẵn; acquisition và xuất PDF được giả lập trong lần kiểm tra UI này.
- `git diff --check` đạt. Không chạy lại acquisition trực tiếp hoặc kiểm tra triển khai Cloud/Gemini trực tiếp trong đợt này.
- `.venv` xác nhận chạy Python 3.12.10 và Streamlit 1.52.2 bên ngoài sandbox. Lỗi thực thi ban đầu thuộc giới hạn sandbox, không kết luận là lỗi môi trường người dùng.

## Góc nhìn nhà đầu tư

| Nhu cầu | Hiện trạng | Ý nghĩa |
| --- | --- | --- |
| Hiểu doanh nghiệp và rủi ro | Có tài chính, vĩ mô, ngành, tin, luận điểm và điều kiện phủ định | Đủ hữu ích cho nghiên cứu ban đầu |
| Kiểm tra độ tin cậy | Có nguồn, kỳ dữ liệu, đối chiếu và chặn khi thiếu đầu vào | Điểm mạnh, nhưng đối chiếu chỉ tiêu chọn không chứng nhận toàn bộ BCTC |
| Biết mức định giá | Có P/E/P/B mẫu, phương pháp đối chiếu và độ nhạy | Giá tham chiếu phụ thuộc mẫu nhỏ và số liệu năm; chưa phải dự phóng lợi nhuận |
| Cập nhật diễn biến kinh doanh | Có bán niên/TTM cho một số trường hợp; adapter còn phụ thuộc mã | Chưa đồng đều giữa các cổ phiếu; cần đọc rõ kỳ đang dùng |
| Chọn giữa nhiều cơ hội | Có mẫu ngành trong báo cáo một mã | Thiếu so sánh trực tiếp các mã người dùng chọn và bộ lọc toàn thị trường |
| Quản lý khoản đầu tư | Có điều kiện theo dõi trong khuyến nghị | Chưa có danh mục, giá vốn, tỷ trọng, tiền mặt, lãi/lỗ và cảnh báo cập nhật |
| Xác định quy mô giao dịch | Có giá/khối lượng lịch sử | Chưa có phân tích sức chứa giao dịch, trượt giá và rủi ro ở cấp danh mục |

## Thứ tự nâng cấp nên ưu tiên

1. **Dữ liệu quý/bán niên và TTM đồng kỳ:** mở rộng theo ngành/mã; thể hiện ngày công bố và kỳ lợi nhuận ngay cạnh giá tham chiếu. Chỉ so bội số khi cơ sở lợi nhuận, phạm vi và ngày giá phù hợp.
2. **Tóm tắt quyết định:** đưa phương pháp, năm tài chính, số peer, độ tin cậy và các điều kiện còn thiếu lên cạnh kết luận. Thể hiện khoảng giá từ các phương pháp và lý do phân tán; không gọi đó là khoảng xác suất.
3. **So sánh 2–5 mã:** cùng kỳ, cùng ngày giá, có tăng trưởng, ROE, chất lượng lợi nhuận, đòn bẩy và bội số; ghi rõ chỉ tiêu không phù hợp từng ngành.
4. **Danh sách theo dõi và cảnh báo:** lưu luận điểm, mốc báo cáo, sự kiện trọng yếu và thay đổi chất lượng dữ liệu. Sau đó bổ sung danh mục với giá vốn, tỷ trọng và rủi ro tập trung.
5. **Kịch bản kinh doanh:** bear/base/bull gắn với doanh thu, biên lợi nhuận, vốn và dòng tiền có nguồn/giả định rõ. Hiện thay đổi P/E/P/B nhập tay chủ yếu là độ nhạy bội số.

Các thiếu hụt trên là hạng mục sản phẩm, chưa được triển khai trong đợt sửa lỗi này. Không nên suy rộng số mã đã kiểm chứng thành khả năng đáng tin cho toàn bộ thị trường.

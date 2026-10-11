# Close và nguồn BCTC vnfinancialdata — 11/10/2026

Biểu đồ, MA20/MA50 và giá đối chiếu định giá dùng Close. Biến động giá, drawdown và độ biến động dùng Adj Close khi chuỗi đầy đủ; nếu không, dùng Close và ghi rõ chưa xác minh điều chỉnh quyền. Không chuẩn hóa biểu đồ Close theo Adj Close. Có chuỗi điều chỉnh từ nhà cung cấp chưa đủ chứng nhận tổng lợi nhuận đầu tư.

## Nguồn và tự động lấy dữ liệu

- SDK [vnfinancialdata 0.1.2](https://pypi.org/project/vnfinancialdata/0.1.2/) và huggingface-hub 1.0.1 được cài qua requirements.txt.
- Dataset công khai [thanhnp-uel/vietnam-listed-companies-financial-statements](https://huggingface.co/datasets/thanhnp-uel/vietnam-listed-companies-financial-statements), bản v1.0.0, commit cố định `a86d37d960c74890d39299d3e400802f832cc789`; không cần API key hoặc token.
- Bảng cân đối kế toán, kết quả kinh doanh, lưu chuyển tiền tệ cho HSX/HNX; snapshot có năm đến 2025. UPCoM chưa được snapshot này hỗ trợ. Không dùng nguồn này để hứa bổ sung F88/VNZ/QNS.
- Mỗi lần phân tích gọi SDK theo mã và sàn; kiểm tra phiên bản, schema, mã, sàn, bảng, khóa trùng, dung lượng và SHA-256 trước khi đọc. Giữ SDK settings gốc sau mỗi lượt; khóa adapter tránh hai yêu cầu đồng thời sửa cấu hình SDK.
- Cache tệp gốc tại data/raw/vnfinancialdata; từ điển kiểm tra checksum và thời hạn cache 24h. Nguồn sau ngày chốt bị loại; lọc năm đến năm trước ngày phân tích. Ngày tạo snapshot không thay cho ngày công bố BCTC.
- Xuất toàn bộ chỉ tiêu gốc ra data/processed/<run_id>_vnfinancialdata.csv; giao diện chọn năm và tải CSV. Hồ sơ nguồn/bảng/checks lưu tại outputs/runs/<run_id>/vnfinancialdata.json và analysis.json.

## Ánh xạ và giới hạn sử dụng

Các chỉ tiêu tiền tệ được ánh xạ bằng mã và tên thực trong từ điển, có quy tắc riêng cho ngân hàng/chứng khoán. Giữ source_file, source_sheet, item_code, tên, giá trị và đơn vị khai báo. Các dòng cùng khái niệm nhưng khác giá trị không tự gộp. Đơn vị từ điển là khai báo của dataset, chưa phải kiểm chứng từng tài liệu gốc. Không dùng khai báo VND chung để nhập EPS hoặc các tỷ số.

Dataset chưa cung cấp đủ ngày công bố, ngày đầu/cuối kỳ và phạm vi hợp nhất/riêng lẻ cho từng bảng. Vì vậy đây là lớp bổ sung: bảng lịch sử, xuất dữ liệu, đối chiếu số cùng năm. Không tự thay đầu vào định giá đã xác minh; không dùng giá trị khớp để chứng nhận nguồn gốc độc lập. Khác quy ước dấu ở chi phí lãi vay/chi tiền được ghi riêng, giữ số gốc và không tính là khớp.

Lỗi lớp bổ sung không làm mất BCTC chính hợp lệ. Giao diện/PDF phân biệt: kỳ chính đang dùng, kỳ KBS bị loại do metadata, chỉ tiêu thực sự thiếu và phương pháp định giá không áp dụng được. DCF âm hoặc P/E không phù hợp không có nghĩa thiếu toàn bộ BCTC.

## Kiểm chứng dữ liệu thực

| Mã | Ba bảng | Năm | Đối chiếu tiền tệ 2025 |
|---|---:|---|---|
| SHS (HNX) | 4.581 dòng | 2011–2025 | 10/10 khớp trong 0,1% |
| VNM (HSX) | 2.801 dòng | 2011–2025 | 13/14 khớp; chi phí lãi vay cùng độ lớn nhưng trái dấu |

VNM: nguồn chính +325.804.350.000 VND, nguồn bổ sung −325.804.350.407 VND. Không đổi dấu để tăng số kiểm tra khớp. SHS vẫn dùng BCTC 2025 đã kiểm chứng từ PDF doanh nghiệp; nguồn mới chưa thay phần này.

134 kiểm thử offline đạt, bao gồm Close/MA tách Adj Close, schema/đơn vị/ánh xạ, dữ liệu tương lai, UPCoM, kết nối lỗi, checksum hỏng, khôi phục SDK và quy ước dấu. Hai pipeline SHS/VNM chạy nguồn thực không có lỗi tổng; đây là kiểm chứng hai mã, không phải toàn thị trường.

AppTest dùng kết quả nguồn thực đã lưu: SHS/VNM không có ngoại lệ, đổi năm 2025 sang 2024 thành công, có nút tải CSV và chú thích Close. PDF chọn nguồn bổ sung có mục vnfinancialdata; khi bỏ chọn, mục này không xuất hiện. Hai PDF 15/14 trang đã render và xem toàn bộ 29 trang, không có phần chữ tràn lề qua kiểm tra tọa độ.

Minh chứng: submission/evidence/shs_close_vnfinancialdata.json và vnm_close_vnfinancialdata.json. PDF mới tại outputs/pdf/SHS_report.pdf và VNM_report.pdf. Web local đã khởi động lại bằng môi trường .venv có SDK mới.

# Nguồn dữ liệu bổ sung

Nguồn tham khảo: https://github.com/Tumiqa/vn-annual-report-miner và DOI https://doi.org/10.5281/zenodo.20949551. Đã tích hợp bộ Parquet tài chính và chỉ mục báo cáo; chưa tích hợp toàn bộ công cụ/tỷ số của dự án tham khảo. Không chạy mã từ repository tham khảo hay sử dụng token trong repository.

## Dữ liệu và quy trình

1. Chốt phiên bản Git trong config/reference_sources.json. Bản đang dùng là afa208bcf8c24a2b7eb5a1fd446084e376e8838a, ghi nhận 09/10/2026. Không dùng phiên bản này cho ngày phân tích trước đó.
2. Tải ba bảng Parquet balance_sheet/income_statement/cash_flow theo HSX hoặc HNX. Lọc đúng ticker, loại năm chưa kết thúc, khóa trùng và giá trị thiếu/vô hạn. Không đổi thiếu thành 0, không gán thu nhập lãi ngân hàng thành doanh thu sản xuất.
3. Giữ giá trị gốc, item_code, item_name, source_file, source_sheet và source_id. Metadata đơn vị/phạm vi/ngày công bố còn thiếu được giữ là unknown/null.
4. Đối chiếu các dòng ánh xạ được với số liệu chính cùng năm, dung sai 0,1%. Khớp giá trị không tự chứng nhận phạm vi hoặc nguồn độc lập; giá trị lệch vẫn giữ nguyên để kiểm tra.
5. Tra chỉ mục BCTN đúng mã ở cả ticker_folder/ticker_file, năm trước năm phân tích, loại bản needs_review và hash không hợp lệ.
6. Tải PDF mới nhất: thử đường CDN CafeF của tên file chỉ mục và chỉ chấp nhận khi cả dung lượng/SHA-256 khớp Zenodo. Nếu chưa khớp, dùng Range để đọc ZIP có chọn lọc. Từ chối HTTP 200 khi yêu cầu Range để tránh tải toàn bộ kho; kiểm tra Content-Range, số byte, ZIP entry, CRC, kích thước và SHA-256.
7. Kiểm tra số trang có text bằng PyMuPDF; phân biệt chủ yếu text, hỗn hợp và scan cần OCR. Chưa coi có text là đã trích/xác minh tài chính.

## Sản phẩm

- UI: bảng lịch sử gốc, đối chiếu cùng năm, CSV và nút tải BCTN gốc.
- PDF: phần `reference` tùy chọn, giá trị gốc chia 10^9 để dễ đọc (không tự gọi là tỷ VND), bảng đối chiếu và trạng thái báo cáo.
- JSON: reference.records/checks/reports, source version, cache/hash metadata, lỗi nguồn riêng và used_in_primary_analysis=false.
- Lưu trữ: data/raw/reference_miner; tệp cache/raw không đẩy lên Git. Snapshot phân tích/bằng chứng có thể tái kiểm tra theo phiên bản nguồn đã chốt.

## Điều kiện để dùng làm nguồn tài chính chính

Cần xác minh từ báo cáo gốc/website công bố: đúng doanh nghiệp, kỳ đầu/cuối và độ dài, hợp nhất/đơn lẻ, đơn vị và ngày công bố. Phải trích đúng dòng/cột, đối chiếu các chỉ tiêu chính và phương trình bảng cân đối. PDF scan phải OCR kèm kiểm tra. Chưa đủ các điều kiện trên thì dữ liệu tiếp tục là tham khảo và không vào định giá.

Mọi truy xuất nguồn do code thực hiện; nhóm không phải nhập tay. Nguồn mới là lịch sử năm, không thay dữ liệu thị trường cuối ngày hay báo cáo cập nhật 2026.

# Từ điển dữ liệu ban đầu

Đề xuất; kiểu dữ liệu và schema Python/JSON sẽ chốt trong P0.

| Bộ dữ liệu | Trường |
|---|---|
| Doanh nghiệp | ticker, name, sector, industry_group, source_id |
| Giá | ticker, date, open, high, low, close, volume, price_basis, source_id |
| Tài chính | ticker, period_end, period_type, statement_scope, metric, value, unit, published_at, source_id |
| Tin tức | ticker, title, published_at, url, source_id, summary |
| Nguồn | source_id, url_or_file, retrieved_at, page_or_table, notes |

Giá trị chuẩn dự kiến: price_basis adjusted/unadjusted; period_type standalone_quarter/cumulative/year; statement_scope consolidated/separate. Adapter cần ánh xạ nguồn rõ ràng.

Ngày ISO 8601; thời điểm có múi giờ. Giá VND/cổ phiếu, tài chính VND, khối lượng cổ phiếu. Giữ đơn vị gốc và hệ số quy đổi trong metadata xử lý.

published_at là ngày công bố, retrieved_at là thời điểm thu thập; hai trường không thay thế nhau. source_id phải tồn tại trong danh mục nguồn, page_or_table truy vết tài liệu gốc.

Thiếu dữ liệu giữ null/NA, không điền 0. AnalysisResult cần giá trị, đơn vị, kỳ, công thức, nguồn và lý do không tính được cho từng chỉ tiêu.

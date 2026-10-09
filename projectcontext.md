# Project context - StockInsight

Cập nhật: 09/10/2026. Thư mục gốc dự án: `gk/`.

## Nguồn và phạm vi công việc

- Đề gốc: `docs/references/261BFF401101_Dethigiuaky.pdf` (bản sao nguyên trạng từ tài liệu người dùng cung cấp).
- Hướng triển khai: `docs/references/implementation_proposal.txt` (nội dung người dùng gửi, là đề xuất kỹ thuật).
- Yêu cầu hiện tại: kiểm thử HPG và tự lấy dữ liệu bằng code vì nhóm chưa có dữ liệu; đề xuất dữ liệu trong phiên hay cuối ngày.
- Giai đoạn hiện tại: giao diện Streamlit gọi trực tiếp pipeline tự lấy giá ngày và tải PDF tài chính HPG mỗi lần bấm Phân tích. Đã có hiển thị dữ liệu/biểu đồ; chưa hoàn thiện chỉ tiêu tài chính và PDF phân tích đầu ra.

Nội dung tài liệu là căn cứ bài tập/phương án. Người dùng đã yêu cầu tự lấy dữ liệu và kiểm thử HPG; chưa có yêu cầu triển khai Internet hoặc nộp bài.

## Yêu cầu từ đề gốc

Tên đề: **Xây dựng hệ thống phân tích cơ hội đầu tư cổ phiếu**.

1. Thiết kế, xây dựng và vận hành hệ thống phân tích cơ hội đầu tư vào cổ phiếu bất kỳ.
2. Tự động trích xuất báo cáo phân tích ra PDF theo nhu cầu người dùng.
3. Bảo đảm dữ liệu chính xác, kết quả phân tích đánh giá thích hợp và có sự sáng tạo.

Các nguồn được đề liệt kê là nguồn có thể khai thác: giá/giao dịch, báo cáo tài chính/chỉ số doanh nghiệp niêm yết, tin tức doanh nghiệp, báo cáo phân tích công ty chứng khoán để tham khảo trình bày và nguồn tài chính/công nghệ phù hợp khác.

Nguồn tham khảo trong đề: https://github.com/Tumiqa/vn-annual-report-miner. Chưa kiểm chứng hoặc tích hợp repository này trong phiên khởi tạo.

Hạn nộp ghi trên đề: **11:30 ngày 09/10/2026**, theo giờ địa phương người dùng (Asia/Saigon). Không suy diễn thời gian còn lại từ lịch 140 phút trong bản đề xuất.

Đề không quy định công nghệ, số nguồn tối thiểu, số trang PDF; không bắt buộc DCF, AI, dự báo giá hoặc triển khai Internet.

## Phương án kỹ thuật ban đầu

Tên làm việc: **StockInsight - Hệ thống phân tích cơ hội đầu tư cổ phiếu Việt Nam**.

Theo bản đề xuất, chọn Python, Streamlit, pandas/numpy, matplotlib, ReportLab và YAML. Lưu dữ liệu ban đầu bằng CSV và JSON; Parquet là lựa chọn bổ sung. Phiên bản thư viện sẽ được kiểm chứng và chốt khi triển khai, chưa cài đặt trong bước khởi tạo.

Ưu tiên luồng tối thiểu: dữ liệu có nguồn -> chuẩn hóa/kiểm tra -> phân tích -> kết quả thống nhất -> giao diện/PDF. Kiểm chứng một mã trước, sau đó thêm ít nhất hai mã khác làm mục tiêu nghiệm thu nội bộ. Thiết kế nhận mã làm tham số; không cố định số liệu theo một doanh nghiệp.

Ngân hàng, chứng khoán và doanh nghiệp phi tài chính cần phương pháp khác nhau. Phạm vi ngành và danh sách mã thực sự có dữ liệu phải được xác định trước khi hiển thị hỗ trợ trên giao diện.

## Luồng người dùng dự kiến

1. Nhập/chọn mã được hỗ trợ.
2. Chọn ngày phân tích, giai đoạn giá và kỳ tài chính khả dụng.
3. Chọn báo cáo tóm tắt/đầy đủ và các phần cần xuất.
4. Chạy phân tích, xem kết quả và tình trạng dữ liệu.
5. Tạo/tải PDF theo đúng lựa chọn.

Các phần dự kiến: tổng quan, giá và giao dịch, tài chính, định giá khi đủ dữ liệu, tin tức, cơ hội/rủi ro, phương pháp/nguồn. Phần phương pháp/nguồn và cảnh báo dữ liệu cần giữ để giải thích kết quả.

## Kiến trúc và trách nhiệm

```text
gk/
  projectcontext.md
  task.md
  README.md
  requirements.txt
  app.py
  config/
    settings.yaml
    analysis_rules.yaml
    valuation_assumptions.yaml
  src/
    models.py
    pipeline.py
    data/          # providers, loaders, normalize, validate
    analysis/      # market, financial, valuation, news, conclusion
    reporting/     # charts, sections, pdf_exporter
  assets/fonts/
  data/
    raw/{prices,financials,news,documents}/
    processed/
    metadata/source_registry.csv
  outputs/runs/
  tests/fixtures/
  docs/
    references/
    architecture.md
    methodology.md
    data_dictionary.md
    demo_script.md
  submission/
```

`src/data/` chứa mã xử lý; `data/` chứa dữ liệu. Font, logo, báo cáo mẫu, video và thư mục từng lần chạy chỉ được tạo khi có nội dung thật, không tạo file nhị phân giả.

`models.py` định nghĩa hợp đồng yêu cầu, dữ liệu và kết quả. `pipeline.py` điều phối đọc dữ liệu, kiểm tra, phân tích và lưu lần chạy. Giao diện và PDF cùng sử dụng một kết quả phân tích, không tính chỉ tiêu riêng.

Mỗi lần chạy dự kiến lưu vào `outputs/runs/<TICKER>_<YYYYMMDD_HHMMSS>/`: `request.json`, `validation.json`, `analysis.json`, `figures/`, `report.pdf`.

## Hợp đồng dữ liệu dự kiến

| Nhóm | Trường chính |
|---|---|
| Doanh nghiệp | ticker, name, sector, industry_group, source_id |
| Giá | ticker, date, open, high, low, close, volume, price_basis, source_id |
| Tài chính | ticker, period_end, period_type, statement_scope, metric, value, unit, published_at, source_id |
| Tin tức | ticker, title, published_at, url, source_id, summary |
| Nguồn | source_id, url_or_file, retrieved_at, page_or_table, notes |

Kết quả phân tích dự kiến gồm request, company, data_status, market, financial, valuation, news, opportunities, risks, sources và assumptions. Mỗi chỉ tiêu cần giá trị/đơn vị/kỳ/công thức/nguồn hoặc lý do không tính được. Hợp đồng Python/JSON chi tiết là công việc tiếp theo.

## Quy tắc chất lượng dữ liệu và phân tích

- Chuẩn hóa giá về VND/cổ phiếu, tài chính về VND; đơn vị hiển thị có thể rút gọn nhưng phải ghi rõ.
- Ghi cơ sở giá điều chỉnh/chưa điều chỉnh và thời điểm giá; không trộn cơ sở giá trong một chuỗi.
- Thiếu dữ liệu giữ trạng thái thiếu, không điền 0 để tạo kết quả.
- Kiểm tra ngày, bản ghi trùng, giá/khối lượng bất hợp lý, phạm vi và kỳ báo cáo.
- Không trộn hợp nhất với riêng lẻ. Phân biệt quý độc lập, lũy kế và năm.
- Chỉ dùng thông tin đã công bố đến ngày phân tích; nếu thiếu ngày công bố, không khẳng định dữ liệu đủ điều kiện cho phân tích lịch sử.
- Chuyển lũy kế sang quý độc lập trước khi cộng TTM. Không tính TTM cho tài sản/vốn chủ sở hữu.
- Mẫu số bằng 0 hoặc cơ sở so sánh không phù hợp: trả trạng thái không xác định và lý do.
- Không diễn giải P/E thông thường khi EPS âm/không phù hợp. EPS phải nhất quán kỳ và điều chỉnh cổ phiếu.
- ROE sử dụng lợi nhuận và vốn bình quân cùng phạm vi; ghi rõ năm/TTM/quý.
- Nhận định dùng quy tắc và mẫu câu có thể kiểm tra, gắn dữ kiện -> tác động -> điều kiện theo dõi.
- Giả định định giá phải ghi nguồn hoặc nhãn giả định người dùng; không dùng ngưỡng mua/bán chung cho mọi ngành.
- Nguồn lỗi có thể dùng bản lưu với thời điểm rõ ràng; dữ liệu mô phỏng nếu dùng để thử phải ghi nhãn và không trình bày như dữ liệu thật.

## Ưu tiên và nghiệm thu dự kiến

Ưu tiên: dữ liệu kiểm chứng được -> luồng phân tích/PDF -> nhận định có căn cứ -> tùy chọn người dùng -> truy vết số liệu. Ba kịch bản định giá, DCF và AI là mở rộng sau MVP.

MVP được xem là đạt khi có luồng chạy bằng dữ liệu thật có nguồn, đổi mã làm kết quả đổi, lựa chọn phần báo cáo tác động đúng đến PDF, số liệu giao diện/PDF khớp, xử lý được thiếu dữ liệu và PDF tiếng Việt đọc tốt. Đối chiếu chỉ tiêu trọng yếu với dữ liệu gốc và kiểm tra đơn vị/kỳ/TTM là bắt buộc trong nghiệm thu nội bộ.

## Điều cần xác định khi triển khai

- Mã đầu tiên, các mã kiểm chứng bổ sung và phạm vi ngành.
- Nguồn giá/tài chính/tin tức thực sự truy cập được, định dạng và ngày công bố.
- Khả năng tận dụng repository tham khảo sau khi thử một mã/một kỳ.
- Font Unicode được phép phân phối, phiên bản thư viện đã thử thành công.
- Thông tin nhóm và hình thức nộp; chưa có trong tài liệu được cung cấp.

Tiến độ cụ thể được quản lý trong `task.md`. Chỉ đánh dấu hoàn thành khi có sản phẩm hoặc bằng chứng kiểm tra tương ứng.

## Kiểm thử HPG và lựa chọn tần suất dữ liệu

Đã chạy `python -m scripts.fetch_data --ticker HPG --start 2025-10-09 --as-of 2026-10-09` thành công. Lượt `HPG_20261009_105621_805649` lấy 261 bản ghi từ 09/10/2025 đến 08/10/2026, qua kiểm tra cấu trúc/ngày/OHLC/khối lượng. Giá được lưu trong `data/processed/`, JSON nguồn trong `data/raw/prices/`, log trong `outputs/runs/`. Đây là kiểm thử khả năng thu thập, chưa phải xác nhận độ chính xác độc lập.

Đề xuất bản đầu dùng dữ liệu cuối ngày, cập nhật tự động khi chạy code. Quy tắc hiện tại thận trọng: chỉ lấy ngày trước ngày hiện tại theo UTC+7, dù chạy sau giờ đóng cửa; không coi thanh giá ngày hiện tại là phiên đã hoàn tất. Ngày cuối có thể cũ hơn cutoff nếu nguồn không có dữ liệu. Chưa có lịch cập nhật nền hoặc chế độ realtime.

Nguồn giá thử nghiệm: Yahoo Finance chart, mã HPG.VN, đơn vị VND từ metadata. Cơ sở điều chỉnh OHLC chưa xác minh, nên ghi `yahoo_chart_ohlc_unverified`; chưa dùng để khẳng định lợi suất điều chỉnh/tổng lợi suất hoặc định giá. Cần đối chiếu nguồn thứ hai và sự kiện vốn trước khi sử dụng báo cáo phân tích.

Đã tải từ trang quan hệ cổ đông Hòa Phát: BCTC hợp nhất soát xét 6 tháng 2026 (công bố 28/08/2026, 67 trang) và BCTC hợp nhất quý II/2026 (30/07/2026, 37 trang). Hai tài liệu có kỳ chồng lấp, không được xem như hai kỳ độc lập để cộng TTM. Chưa trích xuất chỉ tiêu tài chính. Bộ tìm PDF hiện chỉ hỗ trợ HPG và trang danh sách đầu tiên; chưa tìm đủ lịch sử cho mọi ngày phân tích.

5 kiểm thử offline đạt: cutoff theo múi giờ, loại phiên hiện tại, metadata giá, dữ liệu lỗi và ngày công bố/phạm vi báo cáo. Xem `docs/hpg_data_check.md` để biết kết quả và phần còn thiếu.

Người dùng đã xác nhận yêu cầu code tự lấy dữ liệu ngay trong ứng dụng. Bộ thu thập dùng chung tại `src/data/acquisition.py`; `src/pipeline.py` gọi bộ này trước khi tính/hiển thị kết quả. `app.py` có form mã/ngày và nút Phân tích, không đòi CSV hoặc CLI trước. Mỗi lần bấm gọi lại nguồn; nguồn lỗi hiển thị trạng thái, không thay bằng kết quả cũ. CLI chỉ là công cụ tùy chọn. Có thêm 3 kiểm thử pipeline (8 tổng cộng), gồm workspace trống và lỗi nguồn.

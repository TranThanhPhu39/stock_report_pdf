# StockInsight

Ứng dụng phân tích cổ phiếu Việt Nam và tự tạo PDF theo nhu cầu người dùng. **Không cần chuẩn bị data**: mỗi lần bấm Phân tích, chương trình tự lấy giá, tài chính, hồ sơ doanh nghiệp, tin công bố, vĩ mô, doanh nghiệp cùng ngành và đối chiếu nguồn.

## Chạy ứng dụng

Python 3.11+; máy kiểm thử dùng Python 3.12.10. Chạy trong thư mục dự án:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Nhập HPG (hoặc mã Việt Nam có dữ liệu Yahoo/KBS), chọn khoảng ngày, bản đầy đủ/tóm tắt, phần cần xuất, P/B/P/E giả định và các tỷ lệ Ke/WACC/g/thuế trong mục định giá. Bấm **Phân tích**, sau đó **Tải báo cáo phân tích PDF**. Luồng chính không yêu cầu chạy script lấy dữ liệu riêng.

Để đọc PDF scan bán niên HPG tự động, cài Tesseract OCR có gói `vie` và `eng`, thêm `tesseract` vào PATH. Windows cũng nhận đường dẫn `C:/Program Files/Tesseract-OCR/tesseract.exe`. Thiếu OCR: hệ thống báo thiếu phần bán niên và vẫn dùng số liệu năm hợp lệ. Tệp PDF gốc tải lần đầu có thể mất vài phút; bản lưu được kiểm tra SHA-256 và thời hạn 24 giờ trước khi dùng lại. Giá, tài chính và danh sách công bố vẫn được truy cập mới mỗi lượt.

## Dùng dòng lệnh (tùy chọn)

```powershell
python -m scripts.analyze HPG --start 2025-10-09 --as-of 2026-10-09
python -m scripts.analyze VNM --mode summary --sections macro industry financial reference risks --target-pb 2.0
python -m unittest discover -s tests -v
```

Tệp theo lượt chạy nằm tại `outputs/runs/<run_id>/`: request.json, validation.json, acquisition.json, sources.json, analysis.json, charts/, và `<ticker>_report.pdf`. Dữ liệu gốc và bảng chuẩn nằm tại `data/`. PDF và số liệu giao diện dùng chung một kết quả tính toán. PDF tiếng Việt dùng font DejaVu có giấy phép trong `assets/fonts/LICENSE.txt`.

## Phân tích và nguồn

- Giá cuối ngày Yahoo Finance; nếu lỗi tải/OHLC, tự thử toàn chuỗi KBS và đối chiếu ngược bằng Yahoo. Không ghép OHLC khác cơ sở điều chỉnh hoặc tự sửa giá nguồn. Giá đóng cửa phải khớp toàn bộ mẫu tối đa 20 phiên gần nhất; ghi phạm vi thực nhận và khoảng đầu kỳ thiếu. Luôn bỏ ngày hiện tại theo UTC+7, kể cả sau giờ giao dịch.
- Lợi suất theo Yahoo Adj Close, MA20/MA50, drawdown, biến động năm hóa và khối lượng. Chuỗi điều chỉnh không đồng nghĩa lợi nhuận thực nhận sau phí/thuế.
- Báo cáo năm qua KBS: doanh thu thuần, LNST, tài sản, vốn, CFO, tăng trưởng, ROE hợp nhất, biên lợi nhuận và nợ vay/vốn khi phù hợp. Bán niên HPG được đọc trực tiếp từ PDF soát xét của doanh nghiệp bằng OCR.
- Vĩ mô: tự đọc NSO (GDP lũy kế, CPI bình quân, IIP, tín dụng, bán lẻ thực, xuất khẩu…) và World Bank cho lịch sử năm. Lãi suất cho vay và tỷ giá World Bank là số lịch sử, không phải giá hiện tại.
- Ngành: phân loại ICB từ Vietcap, chọn tối đa bốn doanh nghiệp theo tài sản, cùng ngày cuối kỳ/phạm vi báo cáo; so với trung vị mẫu, loại mã đang phân tích. Nếu ngành hẹp không đủ mẫu, mở rộng cấp ICB và ghi rõ. Phân loại khoảng 1.582 mã không có nghĩa đã phân tích/kiểm chứng toàn bộ.
- Định giá tích hợp từ ZIP người dùng: P/B giả định, Gordon theo ROE cổ đông mẹ, trung vị P/B mẫu tự thu thập, P/E lợi nhuận năm quy đổi, DCF FCFF và bình quân trọng số. Mỗi phương pháp có điều kiện và lý do chặn riêng. Không thay NCI null bằng 0; không áp DCF sản xuất cho ngân hàng; không gọi P/E năm là TTM. Xem [phương pháp tích hợp](docs/valuation_upgrade.md).
- Tin công bố có ngày và liên kết. Kết luận quy tắc dùng dữ liệu và mẫu ngành. Gemini là tùy chọn diễn giải từ bundle số liệu/kỳ/ngày chốt/ngành/nguồn, có kiểm tra dẫn nguồn và fallback khi thiếu key/lỗi JSON/API; không đọc toàn văn tin hoặc tạo số liệu mới.

## Kiểm chứng ngày 09/10/2026

Trước đợt tích hợp ZIP, 54 kiểm thử offline đạt và đã chạy dữ liệu thực cho HPG, FPT, VNM, VCB, SSI, MWG, DGC và REE; đây là tám mã kiểm chứng, không phải toàn thị trường. Nút Phân tích thật trên Streamlit đã tự lấy 261 phiên HPG, đọc bán niên và tạo PDF, không có ngoại lệ. HPG và VNM khớp 20/20 giá đóng cửa được đối chiếu. FPT lệch 2/20 phiên (21–22/09/2026), vì vậy định giá bị chặn và báo cáo ghi trạng thái thiếu một phần. Số liệu năm 2025 khớp **các chỉ tiêu chọn đối chiếu**, không phải chứng nhận toàn bộ dữ liệu. Xem `submission/acceptance.json` và `docs/hpg_data_check.md`.

Đợt tích hợp ZIP và sửa ACB: **76 kiểm thử đạt**; chạy lại dữ liệu thực ACB/HPG/VNM, cả ba khớp 20/20 phiên gần nhất. ACB dùng 2.574 phiên KBS từ 15/06/2016, chưa đủ đoạn 20/03–14/06/2016; đã có CFO ngân hàng và P/E năm, P/B chặn do NCI null. HPG có Gordon/P/B ngành/P/E/bình quân, DCF chặn vì FCFF âm; VNM có đủ năm phương pháp. Giao diện thực ACB xuất PDF, thiếu Gemini key được fallback không có ngoại lệ. SDK thật được kiểm thử HTTP giả lập, chưa kiểm chứng API Gemini thật hoặc Streamlit Cloud. Minh chứng: `submission/upgrade_acceptance.json`.

PDF mẫu mới: `outputs/pdf/ACB_report.pdf`, `HPG_report.pdf`, `VNM_report.pdf`; FPT giữ mẫu trước đó. Báo cáo mới có biểu đồ giá, tài chính, nền vĩ mô năm, so sánh ngành, định giá, độ nhạy, bảng rủi ro và nguồn liên kết.

## Giới hạn

Mã cổ phiếu là tham số, không cố định HPG; khả năng có số liệu phụ thuộc nguồn. Có tỷ số riêng ngân hàng (thu nhập lãi, CIR, cho vay/tiền gửi) và chứng khoán (cơ cấu môi giới/cho vay). NIM/NPL/CAR và dư nợ margin chưa được xác minh. VCB/SSI/DGC/REE dùng năm hợp lệ gần nhất 2024 vì metadata kỳ 2025 từ nguồn ghi 24 tháng; báo cáo cảnh báo độ trễ. API công khai có thể thay đổi hoặc giới hạn truy cập. Baseline trong `config/verification_baselines.json` là số tham chiếu đã đọc từ tài liệu gốc, **không thay dữ liệu tự lấy** và chỉ áp dụng đúng kỳ. Không dùng dữ liệu giả khi nguồn lỗi.

`projectcontext.md` ghi phạm vi đề gốc; `task.md` ghi hạng mục đã làm. Đề gốc và đề xuất triển khai trong `docs/references/` được giữ riêng.

Đối chiếu đề cập nhật trong ảnh người dùng (bao gồm vĩ mô/ngành, hạn 16:20 ngày 09/10/2026): `docs/assignment_requirements.md`.

## Nguồn bổ sung từ vn-annual-report-miner

Mỗi lượt phân tích tự lấy Parquet tài chính HSX/HNX và tra danh mục BCTN, tải báo cáo mới nhất của mã đó. Dùng phiên bản cố định trong `config/reference_sources.json`, cache Parquet/danh mục 24 giờ và kiểm tra SHA-256. PDF tải từ CDN CafeF chỉ được chấp nhận nếu khớp SHA-256 và dung lượng trong danh mục Zenodo; nếu không, tải riêng PDF bằng HTTP Range trong ZIP, không tải cả kho. PDF cache được kiểm tra checksum mỗi lượt.

Tab Tài chính có mục nguồn bổ sung, bảng giá trị gốc, đối chiếu cùng năm và nút tải CSV/BCTN gốc. Phần PDF `reference` có thể chọn riêng. Nguồn gốc và ngày truy xuất được lưu trong analysis.json/sources.json; source_file/source_sheet/item_code được giữ cho từng giá trị.

**Parquet chưa có metadata xác minh đơn vị, phạm vi và ngày công bố.** Đây là nguồn bổ sung, chưa tự thay kỳ 2024 hay đầu vào định giá. Khớp giá trị không chứng nhận nguồn độc lập/phạm vi. Phiên bản nguồn sau ngày phân tích bị loại; ngày commit không được coi là ngày công bố BCTC. Các báo cáo scan được thông báo cần OCR thêm. Xem `docs/reference_data.md`.

## Gemini tùy chọn và Streamlit Cloud

Không cần key để lấy dữ liệu, phân tích hoặc tạo PDF. Muốn bật nhận xét Gemini: cấu hình `GEMINI_API_KEY` trong environment hoặc Streamlit Secrets, rồi chọn checkbox Gemini trên ứng dụng. SDK dùng `google-genai==2.29.0`, không dùng `google.generativeai`.

Trong `.streamlit/secrets.toml` (local) hoặc Settings → Secrets trên Streamlit Cloud:

```toml
GEMINI_API_KEY = "YOUR_PRIVATE_KEY"
GEMINI_MODEL = "gemini-flash-latest"
```

Key cũng có thể đặt trong `[gemini]` với tên `api_key`. Model có thể đổi bằng environment `GEMINI_MODEL`; secrets cấp gốc được Streamlit cung cấp như environment. File secrets đã được ignore; không đưa key vào code/Git. CLI `--use-ai` đọc environment. Không tự tải `.env`: nếu dùng file này, cần nạp biến vào environment trước khi chạy. Mỗi request AI có timeout và chỉ gửi dữ liệu công khai đã thu thập; thiếu ngành/key hoặc lỗi API/JSON/dẫn nguồn thì giữ kết luận quy tắc. Những nhận xét qua kiểm tra dẫn nguồn vẫn cần đánh giá về nội dung; đây không phải chứng nhận AI suy luận đúng.

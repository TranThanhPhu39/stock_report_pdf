# StockInsight

Ứng dụng phân tích cổ phiếu Việt Nam và tự tạo PDF theo nhu cầu người dùng. **Không cần chuẩn bị data**: mỗi lần bấm Phân tích, chương trình tự lấy giá, tài chính, hồ sơ doanh nghiệp, tin công bố, vĩ mô, doanh nghiệp cùng ngành và đối chiếu nguồn.

## Chạy ứng dụng

Python 3.11+; máy kiểm thử dùng Python 3.12.10. Chạy trong thư mục dự án:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Nhập HPG (hoặc mã Việt Nam có dữ liệu Yahoo/KBS/Vietcap), chọn khoảng ngày, bản đầy đủ/tóm tắt, phần cần xuất, P/B/P/E giả định và các tỷ lệ Ke/WACC/g/thuế trong mục định giá. Bấm **Phân tích**, sau đó **Tải báo cáo phân tích PDF**. Luồng chính không yêu cầu chạy script lấy dữ liệu riêng.

Để đọc PDF scan bán niên HPG, BCTC năm SSI và TVS tự động, cài Tesseract OCR có gói `vie` và `eng`, thêm `tesseract` vào PATH. Windows cũng nhận đường dẫn `C:/Program Files/Tesseract-OCR/tesseract.exe`. Thiếu OCR: hệ thống báo thiếu phần bán niên và vẫn dùng số liệu năm hợp lệ. Tệp PDF gốc tải lần đầu có thể mất vài phút; bản lưu được kiểm tra SHA-256 và thời hạn 24 giờ trước khi dùng lại. Giá, tài chính và danh sách công bố vẫn được truy cập mới mỗi lượt.

## Dùng dòng lệnh (tùy chọn)

```powershell
python -m scripts.analyze HPG --start 2025-10-09 --as-of 2026-10-09
python -m scripts.analyze VNM --mode summary --sections macro industry financial reference risks --target-pb 2.0
python -m unittest discover -s tests -v
```

Tệp theo lượt chạy nằm tại `outputs/runs/<run_id>/`: request.json, validation.json, acquisition.json, sources.json, analysis.json, charts/, và `<ticker>_report.pdf`. Dữ liệu gốc và bảng chuẩn nằm tại `data/`. PDF và số liệu giao diện dùng chung một kết quả tính toán. PDF tiếng Việt dùng font DejaVu có giấy phép trong `assets/fonts/LICENSE.txt`.

## Phân tích và nguồn

- Giá cuối ngày: tự thử nguyên chuỗi theo thứ tự **Yahoo → KBS HTTP → Vietcap HTTP → vnstock–KBS → vnstock–VCI** nếu lỗi tải/OHLC. Vnstock là thư viện truy cập các nguồn gốc KBS/VCI, không phải một nguồn gốc độc lập mới. Khi đối chiếu, loại mọi kết nối cùng nguồn gốc với giá chính (ví dụ vnstock–KBS không đối chiếu bằng KBS HTTP). Dùng `vnstock==4.0.8`, tên hiện tại của dòng thư viện trước đây gọi là vnstock3; tự cài qua requirements, không cần nhập CSV. Xem [kết nối và giới hạn](docs/vnstock_fallback.md). Không ghép OHLC khác cơ sở điều chỉnh hoặc tự sửa giá nguồn. Định giá kiểm tra riêng giá đóng cửa mới nhất: đúng ngày, đúng giá sử dụng, khớp nguồn thứ hai trong 0,1%. Mẫu lịch sử tối đa 20 phiên có trạng thái riêng; nếu chưa khớp đầy đủ thì giữ biểu đồ đóng cửa nhưng không tính MA/lợi suất/drawdown/biến động năm hóa. Ghi phạm vi thực nhận và khoảng đầu kỳ thiếu. Truy vấn KBS có đệm hai ngày để tránh bỏ phiên cuối, nhưng luôn lọc lại đến ngày chốt; bỏ ngày hiện tại theo UTC+7, kể cả sau giờ giao dịch.
- Biểu đồ và MA20/MA50 dùng Close; định giá dùng giá đóng cửa mới nhất đã đối chiếu. Biến động/drawdown/độ biến động ưu tiên Adj Close đầy đủ từ nguồn; nếu thiếu, dùng Close cùng nguồn và ghi hạn chế điều chỉnh quyền. Có Adj Close không đồng nghĩa đã xác minh toàn bộ sự kiện quyền; không coi thống kê giá là tổng lợi nhuận hoặc tổn thất thực nhận.
- Báo cáo năm qua KBS: doanh thu thuần, LNST, tài sản, vốn, CFO, tăng trưởng, ROE hợp nhất, biên lợi nhuận và nợ vay/vốn khi phù hợp. Bán niên HPG được đọc trực tiếp từ PDF soát xét của doanh nghiệp bằng OCR.
- Vĩ mô: tự đọc NSO (GDP lũy kế, CPI bình quân, IIP, tín dụng, bán lẻ thực, xuất khẩu…) và World Bank cho lịch sử năm. Lãi suất cho vay và tỷ giá World Bank là số lịch sử, không phải giá hiện tại.
- Ngành: phân loại ICB từ Vietcap, chọn tối đa bốn doanh nghiệp theo tài sản, cùng ngày cuối kỳ/phạm vi báo cáo; so với trung vị mẫu, loại mã đang phân tích. Nếu ngành hẹp không đủ mẫu, mở rộng cấp ICB và ghi rõ. Phân loại khoảng 1.582 mã không có nghĩa đã phân tích/kiểm chứng toàn bộ.
- Định giá chính: BVPS/EPS cổ đông mẹ nhân P/B/P/E trung vị mẫu tự lấy, cùng kỳ/phạm vi và ngày giá. P/B ưu tiên cho ngân hàng/chứng khoán, P/E năm ưu tiên cho doanh nghiệp phi tài chính; phương pháp còn lại đối chiếu. Giả định nhập tay, Gordon, DCF và bình quân trọng số nằm trong phụ lục độ nhạy, không quyết định khuyến nghị. Không thay NCI null bằng 0 hoặc gọi P/E năm là TTM. Xem [báo cáo đầu tư và SOTP](docs/investment_research_upgrade.md).
- Vĩ mô/ngành thêm chuỗi VN-Index, Brent futures và mẫu bài công khai có ngày/URL/nội dung từ VnExpress, VnEconomy. Nhận xét tách bằng chứng, suy luận có điều kiện và chỉ tiêu theo dõi. Gemini tùy chọn nhận bundle số liệu cùng trích xuất nội dung bài có giới hạn; kiểm tra dẫn nguồn/độ dài, fallback khi thiếu key/lỗi JSON/API; không tạo số liệu, giá mục tiêu hoặc khuyến nghị.

## Kiểm chứng ngày 09/10/2026

Trước đợt tích hợp ZIP, 54 kiểm thử offline đạt và đã chạy dữ liệu thực cho HPG, FPT, VNM, VCB, SSI, MWG, DGC và REE; đây là tám mã kiểm chứng, không phải toàn thị trường. Nút Phân tích thật trên Streamlit đã tự lấy 261 phiên HPG, đọc bán niên và tạo PDF, không có ngoại lệ. HPG và VNM khớp 20/20 giá đóng cửa được đối chiếu. FPT lệch 2/20 phiên (21–22/09/2026), vì vậy định giá bị chặn và báo cáo ghi trạng thái thiếu một phần. Số liệu năm 2025 khớp **các chỉ tiêu chọn đối chiếu**, không phải chứng nhận toàn bộ dữ liệu. Xem `submission/acceptance.json` và `docs/hpg_data_check.md`.

Đợt tích hợp ZIP và sửa ACB: **76 kiểm thử đạt**; chạy lại dữ liệu thực ACB/HPG/VNM, cả ba khớp 20/20 phiên gần nhất. ACB dùng 2.574 phiên KBS từ 15/06/2016, chưa đủ đoạn 20/03–14/06/2016; đã có CFO ngân hàng và P/E năm, P/B chặn do NCI null. HPG có Gordon/P/B ngành/P/E/bình quân, DCF chặn vì FCFF âm; VNM có đủ năm phương pháp. Giao diện thực ACB xuất PDF, thiếu Gemini key được fallback không có ngoại lệ. SDK thật được kiểm thử HTTP giả lập, chưa kiểm chứng API Gemini thật hoặc Streamlit Cloud. Minh chứng: `submission/upgrade_acceptance.json`.

PDF mẫu mới: `outputs/pdf/ACB_report.pdf`, `HPG_report.pdf`, `VNM_report.pdf`; FPT giữ mẫu trước đó. Báo cáo mới có biểu đồ giá, tài chính, nền vĩ mô năm, so sánh ngành, định giá, độ nhạy, bảng rủi ro và nguồn liên kết.

## Giới hạn

Mã cổ phiếu là tham số, không cố định HPG; khả năng có số liệu phụ thuộc nguồn. Có tỷ số riêng ngân hàng (thu nhập lãi, CIR, cho vay/tiền gửi) và chứng khoán (cơ cấu môi giới/cho vay). NIM/NPL/CAR và dư nợ margin chưa được xác minh. VCB/DGC/REE dùng năm hợp lệ gần nhất 2024 vì metadata kỳ 2025 từ nguồn ghi 24 tháng; báo cáo cảnh báo độ trễ. API công khai có thể thay đổi hoặc giới hạn truy cập. Baseline trong `config/verification_baselines.json` là số tham chiếu đã đọc từ tài liệu gốc, **không thay dữ liệu tự lấy** và chỉ áp dụng đúng kỳ. Không dùng dữ liệu giả khi nguồn lỗi.

`projectcontext.md` ghi phạm vi đề gốc; `task.md` ghi hạng mục đã làm. Đề gốc và đề xuất triển khai trong `docs/references/` được giữ riêng.

Đối chiếu đề cập nhật trong ảnh người dùng (bao gồm vĩ mô/ngành, hạn 16:20 ngày 09/10/2026): `docs/assignment_requirements.md`.

## Nguồn bổ sung từ vn-annual-report-miner

Mỗi lượt phân tích tự lấy Parquet tài chính HSX/HNX và tra danh mục BCTN, tải báo cáo mới nhất của mã đó. Dùng phiên bản cố định trong `config/reference_sources.json`, cache Parquet/danh mục 24 giờ và kiểm tra SHA-256. PDF tải từ CDN CafeF chỉ được chấp nhận nếu khớp SHA-256 và dung lượng trong danh mục Zenodo; nếu không, tải riêng PDF bằng HTTP Range trong ZIP, không tải cả kho. PDF cache được kiểm tra checksum mỗi lượt.

Tab Tài chính có mục nguồn bổ sung, bảng giá trị gốc, đối chiếu cùng năm và nút tải CSV/BCTN gốc. Phần PDF `reference` có thể chọn riêng. Nguồn gốc và ngày truy xuất được lưu trong analysis.json/sources.json; source_file/source_sheet/item_code được giữ cho từng giá trị.

**Parquet chưa có metadata xác minh đơn vị, phạm vi và ngày công bố.** Đây là nguồn bổ sung, chưa tự thay kỳ 2024 hay đầu vào định giá. Khớp giá trị không chứng nhận nguồn độc lập/phạm vi. Phiên bản nguồn sau ngày phân tích bị loại; ngày commit không được coi là ngày công bố BCTC. Các báo cáo scan được thông báo cần OCR thêm. Xem `docs/reference_data.md`.

## Nguồn vnfinancialdata

Ứng dụng tự lấy ba bảng BCTC qua `vnfinancialdata==0.1.2`, bản dữ liệu cố định v1.0.0 cho HSX/HNX đến năm 2025; không cần API key. Tab Tài chính có chọn năm, bảng số liệu gốc, đối chiếu cùng năm và tải toàn bộ CSV. PDF mục “Dữ liệu báo cáo bổ sung” có bảng và nguồn này. SHS lấy được 4.581 dòng, VNM 2.801 dòng; 134 kiểm thử offline đạt.

Nguồn mới chưa có đủ metadata phạm vi/ngày công bố từng kỳ để tự thay đầu vào định giá; chưa có UPCoM trong snapshot. Đối chiếu khớp số không chứng nhận nguồn gốc độc lập. Xem [cách sử dụng và minh chứng](docs/vnfinancialdata_upgrade.md).

## Gemini tùy chọn và Streamlit Cloud

Không cần key để lấy dữ liệu, phân tích hoặc tạo PDF. Muốn bật nhận xét Gemini: cấu hình `GEMINI_API_KEY` trong environment hoặc Streamlit Secrets, rồi chọn checkbox Gemini trên ứng dụng. SDK dùng `google-genai==2.29.0`, không dùng `google.generativeai`.

Trong `.streamlit/secrets.toml` (local) hoặc Settings → Secrets trên Streamlit Cloud:

```toml
GEMINI_API_KEY = "YOUR_PRIVATE_KEY"
GEMINI_MODEL = "gemini-flash-latest"
```

Key cũng có thể đặt trong `[gemini]` với tên `api_key`. Model có thể đổi bằng environment `GEMINI_MODEL`; secrets cấp gốc được Streamlit cung cấp như environment. File secrets đã được ignore; không đưa key vào code/Git. CLI `--use-ai` đọc environment. Không tự tải `.env`: nếu dùng file này, cần nạp biến vào environment trước khi chạy. Mỗi request AI có timeout và chỉ gửi dữ liệu công khai đã thu thập; thiếu ngành/key hoặc lỗi API/JSON/dẫn nguồn thì giữ kết luận quy tắc. Những nhận xét qua kiểm tra dẫn nguồn vẫn cần đánh giá về nội dung; đây không phải chứng nhận AI suy luận đúng.

## Sửa điều kiện giá NVL (09/10/2026)

88 kiểm thử đạt. Giá mới nhất được kiểm tra bằng bản ghi đối chiếu thực tế, không chỉ bằng cờ trạng thái. Lệch/thiếu các phiên lịch sử không chặn giá mới nhất đã khớp; giá mới nhất sai/thiếu/cũ, giá sử dụng khác bản ghi hoặc sai lệch >0,1% vẫn chặn định giá. UI/PDF tách hai trạng thái. Khi mẫu lịch sử chưa khớp, không tính MA20/50, lợi suất, drawdown hoặc biến động năm hóa; vẫn hiển thị chuỗi đóng cửa có cảnh báo. Các kiểm tra tài chính/NCI/phạm vi/CP snapshot vẫn giữ. Bấm **Phân tích** lại để thay kết quả cũ trong phiên giao diện. Chứng cứ chạy NVL: `submission/nvl_price_scope.json`.

## PDF hai cột và HNX/UPCoM (11/10/2026)

PDF đã chuyển sang biểu đồ ở cột trái, phân tích ở cột phải xuyên suốt từng phần; phụ lục phương pháp/nguồn dùng toàn chiều rộng. Có khuyến nghị nghiên cứu ngay trang đầu và luận điểm đầu tư kèm bằng chứng, điều kiện xác nhận/bác bỏ, kỳ và nguồn. Khuyến nghị được tính bằng quy tắc, không cần API Gemini. Sau cập nhật hãy khởi động lại ứng dụng và bấm **Phân tích và tạo PDF** để tạo báo cáo mới.

Đợt bố cục/nguồn tại commit 7634381 đã sửa đối chiếu Yahoo thiếu mã bằng Vietcap, ngày kết thúc truy vấn KBS, bộ đọc ba kỳ F88 và CFO chứng khoán. Khi đó 101 kiểm thử đạt, sáu mã nguồn thực VNM/SHS/VNZ/PVS/QNS/F88 khớp 20/20 phiên. Minh chứng lịch sử: [bố cục và nguồn](docs/exchange_report_upgrade.md), `submission/exchange_report_acceptance.json`.

Cập nhật SHS tiếp theo: **112 kiểm thử đạt**; tự đọc bảng kiểm toán 2025 trong BCTN có công bố chính thức, đối chiếu 12 giá trị hai năm, so sánh ngành/P/B mẫu đồng kỳ 2025. Khuyến nghị **THEO DÕI** vì LNTT đã thực hiện giảm dù LNST tăng. PDF đã kiểm tra 14 trang tại `outputs/pdf/SHS_report.pdf`. Lỗi thử Yahoo 404 lưu trong hồ sơ; không hiện thành lỗi báo cáo khi nguồn dự phòng thành công. F88 còn thiếu 2025 hợp lệ; QNS chưa đủ hai nhóm định giá. Chi tiết: [nguồn và kiểm chứng SHS](docs/shs_issuer_upgrade.md).

## Cập nhật báo cáo SSI (11/10/2026)

SSI tự đọc BCTC hợp nhất kiểm toán 2025 từ PDF chính thức công bố 27/03/2026; qua 12 đối chiếu giá trị với KBS, cân đối tài sản và lợi nhuận thực hiện/chưa thực hiện. Kỳ KBS sai metadata 24 tháng vẫn bị loại. TVS trong mẫu ngành có bộ đọc PDF kiểm toán tương tự; lần kiểm chứng SSI dùng hai mẫu VDS/TVS cùng kỳ 2025, đủ P/E và P/B. Mẫu nhỏ không đại diện toàn ngành; giá trị năm quy đổi theo số CP snapshot, chưa phải TTM/dự phóng. SSI chưa tích hợp BCTC quý/bán niên 2026.

Khoảng ngày đầu trang là lịch sử giá; ngày chốt giới hạn tài liệu được công bố. Web có nến OHLC, khối lượng, MA20/50 khi lịch sử đủ điều kiện và bộ lọc biểu đồ. Tin vĩ mô/ngành lấy tối đa 8 bài phù hợp mỗi phạm vi trong 30 ngày, gộp một ô mỗi mục; mặc định 3 bài với nút mở toàn bộ. Những mã không vào mẫu có lý do riêng: lỗi kỳ, khác phạm vi, thiếu chỉ tiêu hoặc tải nguồn thất bại.

Gemini chỉ diễn giải bằng chứng vĩ mô/ngành và kênh tác động tới doanh nghiệp; nguồn được gắn từ evidence IDs. Nhận xét sai bị loại riêng, nhận xét hợp lệ được giữ. Lỗi JSON và lỗi kiểm tra được giải thích cụ thể; không tự chứng nhận tính đúng đắn của suy luận AI. Ngày 11/10/2026, sau khi được người dùng cho phép gửi bằng chứng SSI tới Google, khóa trong Secrets đọc được thông tin `gemini-flash-latest`; hai lần tạo nhận xét trả HTTP 504 và 503. Chưa có nhận xét API thật thành công để đưa vào PDF; Cloud chưa kiểm chứng. Yêu cầu hiện giới hạn 60 giây/lần, một lần gọi SDK, tối đa 8.192 token đầu ra; lỗi dịch vụ có mã HTTP rõ ràng và giữ phân tích quy tắc. Xem `submission/evidence/ssi_gemini_live.json`.

PDF SSI mẫu có biểu đồ trái, chữ phải; nguồn dùng tên đơn vị thay S1/S2, nhãn và kích thước biểu đồ đã chỉnh. Chi tiết và giới hạn: [nâng cấp SSI](docs/ssi_report_upgrade.md). Khi cập nhật code, tải lại web và bấm **Phân tích và tạo PDF** để thay kết quả cũ.

Đã bổ sung `packages.txt` cho OCR trên Streamlit Community Cloud theo [hướng dẫn dependency hệ thống](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies). Đây là cấu hình chuẩn bị triển khai, chưa xác nhận ứng dụng Cloud thực tế.

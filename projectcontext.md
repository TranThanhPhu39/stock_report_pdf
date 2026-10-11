# Project context — StockInsight

Cập nhật 09/10/2026. Mục tiêu: ứng dụng nhận mã cổ phiếu và nhu cầu nội dung, tự lấy dữ liệu, phân tích cơ hội/rủi ro, tạo báo cáo PDF tiếng Việt có nguồn và phương pháp rõ ràng.

## Yêu cầu và phạm vi

Đề gốc một trang: `docs/references/261BFF401101_Dethigiuaky.pdf`. Yêu cầu thiết kế, xây dựng và chạy hệ thống phân tích cơ hội đầu tư cho một mã cổ phiếu bất kỳ; tự động tạo PDF theo nhu cầu người dùng; dữ liệu chính xác, phương pháp phù hợp, có tính sáng tạo. Đề không bắt buộc AI, DCF, realtime, triển khai Internet hay số trang cố định.

`docs/references/implementation_proposal.txt` là đề xuất kỹ thuật người dùng cung cấp, không phải mọi mục đều là yêu cầu bắt buộc của đề. Yêu cầu trực tiếp bổ sung: code phải tự lấy data, thử HPG trước, tạo context/task và đưa dự án lên repository `TranThanhPhu39/stock_report_pdf`. Repository đã được khởi tạo/push trong giai đoạn trước.

## Thiết kế đã thực hiện

Python + Streamlit + pandas + matplotlib + ReportLab + PyMuPDF; Tesseract vie/eng để đọc PDF scan. Mã là tham số; phạm vi nguồn hiện tại là cổ phiếu Việt Nam có Yahoo/KBS. Kiểm chứng HPG, FPT, VNM, VCB, SSI, MWG, DGC và REE; không tuyên bố đã chạy toàn thị trường. Những chỉ tiêu không phù hợp/thiếu dữ liệu được bỏ kèm lý do.

Luồng: AnalysisRequest → acquire giá/PDF → collect_research tài chính/hồ sơ/tin/giá đối chiếu → chuẩn hóa kỳ/đơn vị → phân tích → kiểm tra tài chính → kết luận → lưu analysis.json → giao diện và PDF từ cùng kết quả. UI/CLI tự gọi luồng, không cần file CSV có sẵn.

Nguồn: Yahoo chart cho giá; KBS cho báo cáo năm/hồ sơ/tin và giá đối chiếu; Hòa Phát cho PDF hợp nhất soát xét bán niên. Các giá trị đầu vào có source_id, kỳ, ngày công bố, đơn vị và vị trí nguồn; kết quả chỉ tiêu có công thức và inputs. Giá hiện tại luôn dùng phiên trước ngày hiện tại UTC+7. Financial publication và source revision sau ngày phân tích bị loại.

API KBS pageSize 1/2 có thể gắn dữ liệu cũ vào năm mới; dữ liệu quý có Head trùng ID. Chỉ nhận bốn kỳ năm có ánh xạ ID 1..4, năm riêng biệt và cùng phạm vi; không cộng quý lũy kế hoặc tuyên bố P/E TTM. ROE dùng LNST hợp nhất / VCSH hợp nhất bình quân. Định giá là kịch bản P/B có giả định vốn năm giữ nguyên trên số CP hiện tại, không phải dự báo giá.

## Kết quả kiểm chứng

54 kiểm thử offline đạt; giao diện thật tự lấy 261 phiên HPG và tạo PDF không lỗi. HPG/VNM khớp 20 phiên giá, FPT có hai phiên lệch và định giá bị chặn. Các tài chính năm chọn đối chiếu khớp tài liệu gốc; bán niên HPG có kiểm tra tài sản = nợ + vốn và cột đầu năm đối chiếu số liệu năm 2025. Ba PDF mẫu có nguồn và giới hạn. Chưa chứng nhận mọi cổ phiếu, mọi kỳ và mọi ngành.

## Quyết định phát triển

Không thay null bằng 0 hoặc dùng số liệu giả khi nguồn lỗi. Không dùng số CP hiện tại cho định giá quá khứ. Không coi số liệu OCR là hợp lệ khi thiếu kiểm tra bảng cân đối. Giá lệch nguồn thì chặn định giá. Người dùng chọn phần và mức chi tiết; nguồn, phương pháp và trạng thái dữ liệu luôn giữ trong PDF. PDF gốc được cache 24 giờ có SHA-256; OCR cache theo checksum nội dung. Font DejaVu có giấy phép phân phối đi kèm.

Các mở rộng không bắt buộc còn lại: NIM/NPL/CAR ngân hàng và rủi ro margin chuyên sâu; tự tìm PDF mọi doanh nghiệp; bốn quý đã xác minh để tính TTM/P/E; realtime; triển khai web; AI đọc toàn văn tin.

## Đề cập nhật và phần bổ sung

Ảnh đề người dùng cung cấp yêu cầu rõ tổng quan vĩ mô, phân tích ngành và cơ hội đầu tư, hạn 16:20 ngày 09/10/2026. Ảnh này bổ sung phạm vi so với PDF lưu trước đó; áp dụng nội dung mới khi đối chiếu nghiệm thu.

Luồng bổ sung: tài chính hợp lệ → collect_context → NSO/World Bank và ICB/so sánh KBS → analyze_context → luận điểm vĩ mô–ngành–doanh nghiệp → UI/PDF. Không cần nhóm chuẩn bị dữ liệu. Vĩ mô giữ kỳ đo/ngày công bố; lịch sử World Bank giữ ngày cập nhật riêng. Phân loại ICB là ảnh chụp hiện tại, không chứng nhận ngành trong quá khứ. Mẫu so sánh tối đa bốn mã, cùng ngày cuối kỳ/phạm vi/nhóm tài chính, không đại diện chỉ số ngành.

Ngân hàng có CIR và cho vay/tiền gửi; chứng khoán có cơ cấu doanh thu. Kỳ năm phải dài 12 tháng và kết thúc trước ngày công bố/ngày phân tích. VCB/SSI/DGC/REE kỳ 2025 bị loại do metadata 24 tháng; sử dụng 2024 kèm cảnh báo. HPG lấy thêm bán niên 2026 trực tiếp qua OCR. Giao diện đã kiểm thử phần vĩ mô/ngành và xuất PDF chỉ chứa hai phần này. Bằng chứng tám lượt thực được lưu trong submission/evidence.

## Nguồn tham khảo được tích hợp

Tự lấy Parquet tài chính HSX/HNX và BCTN nhiều mã từ danh mục vn-annual-report-miner/Zenodo. Bản nguồn được chốt theo commit; cache có hash, PDF mirror phải khớp checksum danh mục hoặc tải riêng bằng Range. UI/CSV/PDF có dữ liệu bổ sung và bảng đối chiếu. Không tự dùng Parquet vào định giá vì còn thiếu đơn vị/phạm vi/ngày công bố. VCB/SSI/DGC/REE vẫn giữ kỳ chính hợp lệ 2024, đồng thời có dữ liệu tham khảo/BCTN 2025 để tiếp tục xác minh.

## Cập nhật ZIP và sửa ACB (09/10/2026)

Đã tích hợp định giá đa phương pháp từ ZIP, có chỉnh các cơ sở chưa phù hợp; chi tiết docs/valuation_upgrade.md và provenance bản gốc. Thêm nguồn giá KBS thay cả chuỗi khi Yahoo lỗi, đối chiếu ngược Yahoo, báo phạm vi thực nhận. Ngân hàng có CFO đúng mã, thu nhập lãi/tổng thu nhập hoạt động, tăng trưởng tín dụng và kết luận lợi nhuận độc lập. PDF có sáu nhóm biểu đồ, bảng rủi ro và nguồn tại luận điểm.

76 kiểm thử đạt; dữ liệu thực ACB/HPG/VNM và UI thật ACB. ACB chưa đủ đoạn đầu 2016 và NCI, có P/E năm quy đổi; HPG FCFF âm nên DCF chặn; VNM đủ phương pháp. Gemini tùy chọn từ bundle số liệu/nguồn, key qua Secrets/environment; missing key/API/JSON có fallback. SDK thật đã test HTTP giả lập, chưa test API/deploy thật. Không coi P/E năm là TTM; không coi số ngành cố định ZIP là dữ liệu thị trường. Minh chứng submission/upgrade_acceptance.json.

Cập nhật NVL: định giá dùng giá mới nhất có bản ghi đúng ngày/giá khớp hai nguồn trong 0,1%; mẫu lịch sử giữ kiểm tra độc lập, chưa khớp thì chặn thống kê chuỗi. 88 kiểm thử đạt; không bỏ kiểm tra tài chính.

## Bố cục và khuyến nghị (11/10/2026)

Phản hồi mới của người dùng yêu cầu cột trái là biểu đồ, cột phải là nội dung phân tích, giống bố cục mẫu CFO. Bản mới dùng frame phải 112 mm và vùng biểu đồ trái 56 mm cho các phần phân tích, không chỉ đặt biểu đồ cạnh chú thích ngắn. Phụ lục phương pháp/nguồn toàn chiều rộng. PDF, UI và analysis.json dùng chung recommendation: stance, căn cứ, thời gian theo dõi, mức tin cậy, kịch bản tham chiếu, luận điểm có nguồn/điều kiện xác nhận/bác bỏ.

Nguồn tự lấy mở rộng Vietcap gap-chart cho HNX/UPCoM khi Yahoo không có mã. KBS có đệm truy vấn cuối kỳ nhưng lọc lại <= ngày chốt; không ghép chuỗi khác nguồn. Bộ đọc ba kỳ chỉ nhận khi Head liên tiếp và Value4 trống; CFO chứng khoán dùng mã 4735. Đợt commit 7634381 có sáu mã thực, 101 tests và ba PDF; khi đó SHS/F88 thiếu 2025. Minh chứng lịch sử: docs/exchange_report_upgrade.md và submission/exchange_report_acceptance.json.

SHS đã bổ sung bảng kiểm toán riêng lẻ 2025 từ PDF BCTN có công bố chính thức, kiểm tra ngày/đơn vị/phạm vi/cột/hàng/cân đối và đối chiếu 12 giá trị với KBS. Metadata KBS 24 tháng vẫn bị loại. Cache trang công bố/PDF có checksum trong 24h tránh mất số liệu khi DNS tạm lỗi. Thống kê thiếu Adj Close dùng đóng cửa nguồn có nhãn hạn chế điều chỉnh quyền, không gọi là tổng lợi nhuận. Khuyến nghị SHS THEO DÕI dựa trên LNTT đã thực hiện giảm dù LNST tăng. 112 tests đạt, pipeline thực không lỗi, AppTest không ngoại lệ, PDF 14 trang đã xem toàn bộ. F88/QNS chưa được adapter này bổ sung. Xem docs/shs_issuer_upgrade.md và submission/evidence/shs_issuer_upgrade.json.

Yêu cầu thêm vnstock3: tích hợp tên gói hiện tại vnstock 4.0.8 thành kết nối dự phòng sau Yahoo/KBS/Vietcap, gồm KBS và VCI. Kiểm tra metadata, đơn vị nghìn VND -> VND, OHLCV và ngày chốt; không bổ sung Adj Close giả. Loại nguồn gốc trùng giữa SDK/HTTP khi đối chiếu. 119 kiểm thử offline đạt; SHS/VNZ/F88 chạy hai kết nối thực đều khớp 20/20 phiên với nguồn gốc khác. Bổ sung này chỉ áp dụng giá chính/đối chiếu, chưa thay bộ đọc tài chính hoặc giá peer ngành. Xem docs/vnstock_fallback.md.

11/10/2026: tách biểu đồ/MA/giá định giá dùng Close khỏi thống kê dùng Adj Close theo nguồn. Tích hợp vnfinancialdata 0.1.2 qua SDK với dataset v1.0.0/SHA cố định, đủ ba bảng tự tải và xuất toàn bộ CSV. SHS có 4.581 dòng, VNM 2.801 dòng đến 2025; đối chiếu 2025 tương ứng 10/10 và 13/14, chi phí lãi vay VNM khác quy ước dấu được giữ nguyên. Nguồn chỉ bổ sung do chưa rõ phạm vi/ngày công bố từng kỳ, chưa có UPCoM; không tự thay dữ liệu định giá. Chẩn đoán tài chính phân biệt metadata kỳ bị loại, chỉ tiêu thiếu và hạn chế phương pháp. 134 kiểm thử đạt. Xem docs/vnfinancialdata_upgrade.md.

## Báo cáo đầu tư theo phản hồi mới (11/10/2026)

Giá chính từ bội số mẫu đồng kỳ/ngày giá và EPS/BVPS cổ đông mẹ; P/B ưu tiên ngành tài chính, P/E năm ưu tiên phi tài chính. Giả định nhập tay chỉ tác động phụ lục độ nhạy. Khuyến nghị không dùng bình quân trọng số kịch bản. Tin vĩ mô/ngành tự lấy RSS và trích xuất nội dung công khai có giới hạn; VN-Index/Brent là nguồn quan sát riêng, chưa được xác nhận độc lập. Nhận xét luôn tách bằng chứng/kỳ/nguồn khỏi suy luận có điều kiện và điều cần theo dõi.

SOTP có engine xác minh bridge/CP/các mảng không trùng; adapter tự động hiện chỉ REE từ SSI. Báo cáo 10/11/2025 là tham khảo lịch sử, không mở khuyến nghị khi tài chính chính REE vẫn 2024. Không tự ước lượng giá trị mảng từ doanh thu. 155 tests đạt; nguồn thực SHS/VNM/REE, chưa phải toàn thị trường; Gemini thật/Cloud chưa kiểm chứng. Xem docs/investment_research_upgrade.md.

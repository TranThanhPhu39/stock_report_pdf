# Task — StockInsight

Cập nhật 09/10/2026. Các yêu cầu chính đã có luồng chạy thực; không coi đề xuất mở rộng là điều kiện bắt buộc của đề gốc.

## Đã hoàn thành

- [x] Sửa UX web: bỏ JSON mẫu ngành, thêm bảng lý do loại bằng tiếng Việt, thống nhất tab, đưa khuyến nghị lên đầu; tin mặc định 3 bài với nút mở/thu gọn. AppTest SHS/VNM/REE, màn hình ban đầu và nguồn không có tin đạt; chưa kiểm tra trực quan bằng trình duyệt trong phiên này.

- [x] Đọc đề PDF và đề xuất, phân biệt yêu cầu người dùng với nội dung tài liệu.
- [x] Tạo cây thư mục, context/task và repository GitHub.
- [x] UI nhận mã, khoảng ngày, ngày phân tích, mức chi tiết, phần PDF, P/B giả định.
- [x] Code tự lấy giá, tài chính năm, hồ sơ doanh nghiệp và tin công bố, không yêu cầu data nhập tay.
- [x] Tự tìm/tải PDF hợp nhất HPG; cache 24h kiểm tra checksum; đọc PDF scan bằng OCR.
- [x] Giữ raw sources, kỳ, đơn vị, ngày công bố/cập nhật, phạm vi và vị trí nguồn.
- [x] Kiểm tra OHLC, ngày trùng, tiền/volume, metadata bốn kỳ năm; chặn phản hồi kỳ mơ hồ.
- [x] Đối chiếu giá nguồn thứ hai và chỉ tiêu tài chính chọn từ tài liệu gốc; ghi rõ mức kiểm chứng.
- [x] Tính return/MA/drawdown/volatility, tăng trưởng, ROE bình quân, biên lợi nhuận, nợ/vốn, CFO/LNST khi phù hợp.
- [x] Không trộn hợp nhất/đơn lẻ, năm/quý lũy kế; giữ null và lý do cho chỉ tiêu thiếu.
- [x] P/B tham chiếu, ba kịch bản người dùng; chặn khi dữ liệu không đạt điều kiện.
- [x] Nhận định có dữ kiện và điều kiện theo dõi; tin có ngày/link, không suy diễn toàn văn.
- [x] Xuất PDF tiếng Việt có biểu đồ/bảng/nguồn; thực sự áp dụng summary/full và phần chọn.
- [x] UI/PDF dùng chung AnalysisResult; lưu request, validation, acquisition, sources, analysis, chart và PDF theo lượt.
- [x] Font Unicode có giấy phép, dependency có phiên bản kiểm thử, README và tài liệu phương pháp/demo cập nhật.
- [x] 54 kiểm thử offline đạt.
- [x] Streamlit HPG thật: 261 phiên, OCR bán niên hợp lệ, PDF tồn tại, không ngoại lệ.
- [x] Streamlit FPT thật: chọn summary/market/financial/risks, PDF bỏ phần khác, định giá bị chặn đúng.
- [x] Yêu cầu sai xóa kết quả/PDF lượt trước, không trả kết quả cũ.
- [x] Tám lượt dữ liệu thực HPG/FPT/VNM/VCB/SSI/MWG/DGC/REE và ba PDF mẫu; xem acceptance.json.
- [x] Kiểm tra hiển thị tất cả trang PDF mẫu, chữ tiếng Việt, bảng và nguồn.

## Hạn chế đã công bố

FPT có hai phiên giá lệch nguồn, được ghi cảnh báo/chặn P/B. Baseline chỉ kiểm chứng một số chỉ tiêu đúng kỳ. Bộ tỷ số đầy đủ đã kiểm thử ở doanh nghiệp phi tài chính; ngân hàng/chứng khoán có tỷ số riêng; chưa có NIM/NPL/CAR hoặc dư nợ margin xác minh. PDF scan bán niên hiện tự trích chỉ cho HPG. Thiếu nguồn/thiếu OCR được thông báo, không dùng dữ liệu giả.

## Mở rộng ngoài phạm vi bắt buộc

- [ ] Tự khám phá và kiểm tra PDF cho mọi doanh nghiệp.
- [ ] Bổ sung NIM/NPL/CAR và rủi ro margin khi có nguồn xác minh.
- [ ] Adapter bốn quý độc lập đã xác minh để tính TTM/P/E.
- [ ] Phân tích toàn văn tin, dự báo hoặc DCF có giả định được thẩm định.
- [ ] Realtime/triển khai Internet nếu người dùng yêu cầu.

Bộ bàn giao: README, projectcontext/task, docs, outputs/pdf và submission. Minh chứng snapshot trong submission/evidence là kết quả cố định của lượt kiểm thử, không phải nguồn đầu vào bắt buộc của chương trình.

## Bổ sung theo ảnh đề cập nhật

- [x] Tự lấy vĩ mô NSO và lịch sử World Bank, có kỳ đo/ngày công bố/ngày cập nhật.
- [x] Tổng quan GDP, CPI, công nghiệp, tín dụng, tiêu dùng, đầu tư, xuất khẩu; công bố rõ độ trễ lãi suất/tỷ giá lịch sử.
- [x] Tự phân loại ICB từ Vietcap; fallback KBS khi nguồn phân loại lỗi.
- [x] Tự lấy tài chính cùng ngành, chọn tối đa bốn mã, so sánh trung vị cùng kỳ/phạm vi, loại mã mục tiêu khỏi mẫu.
- [x] Mở rộng cấp ngành khi thiếu mẫu, nêu cấp ngành thực dùng và các mã bị loại.
- [x] Liên kết vĩ mô → ngành → dữ kiện doanh nghiệp bằng nhận định có điều kiện.
- [x] Tỷ số ngân hàng/chứng khoán phù hợp; loại kỳ 24 tháng sai metadata.
- [x] Tab và PDF vĩ mô/ngành; kiểm thử lựa chọn hai phần ở chế độ tóm tắt.
- [x] Đối chiếu yêu cầu đề cập nhật và giới hạn kiểm chứng trong docs/assignment_requirements.md.

## Bổ sung dữ liệu từ repository tham khảo

- [x] Tự tải Parquet theo sàn và mã; giữ nguồn/khóa/giá trị gốc.
- [x] Chốt phiên bản, cache 24h và kiểm tra checksum.
- [x] Tự tra BCTN, tải PDF nhiều mã bằng mirror khớp hash hoặc Range ZIP.
- [x] Đối chiếu giá trị cùng năm, nêu rõ sai lệch/metadata chưa xác minh.
- [x] UI/CSV/PDF cho nguồn bổ sung; nút tải BCTN gốc.
- [x] Giữ dữ liệu bổ sung ngoài đầu vào định giá khi chưa đủ kiểm chứng.
- [x] Kiểm thử chống tải cả ZIP, từ chối mirror sai hash, cache hỏng, khóa trùng, thiếu/vô hạn và phiên bản sau ngày phân tích.
- [ ] Xác minh đầy đủ đơn vị/phạm vi/ngày công bố từ PDF, OCR scan nhiều mã và chứng nhận kỳ 2025 trước khi dùng làm nguồn chính.

## Sửa dữ liệu ACB và tích hợp ZIP

- [x] Đọc/lưu provenance code định giá ZIP; tích hợp phương pháp với kiểm tra điều kiện.
- [x] Fallback toàn chuỗi KBS khi Yahoo lỗi, giữ snapshot/validation, đối chiếu nguồn khác.
- [x] Hiển thị phạm vi thực nhận và khoảng đầu kỳ thiếu, tách chế độ báo cáo khỏi chất lượng dữ liệu.
- [x] Ánh xạ CFO ngân hàng, mẫu chỉ tiêu riêng và kết luận lợi nhuận không phụ thuộc doanh thu.
- [x] P/B, Gordon, P/B ngành từ mẫu tự lấy, P/E năm, DCF FCFF + bridge, bình quân trọng số.
- [x] UI/CLI nhập P/E, Ke, WACC, g, tăng trưởng và thuế; lý do chặn từng phương pháp.
- [x] Gemini tùy chọn, bundle dữ liệu/nguồn, xác minh JSON/dẫn nguồn, fallback, Secrets/environment.
- [x] PDF tóm tắt/KPI/biểu đồ/độ nhạy/bảng rủi ro/nguồn liên kết theo cấu trúc CFO tham khảo.
- [x] 76 tests; SDK thật HTTP giả lập; nguồn thực ACB/HPG/VNM; UI thật ACB thiếu key vẫn xuất PDF.
- [ ] Kiểm chứng API Gemini thật và Streamlit Cloud khi có key/môi trường deploy.
- [ ] Xác minh NCI ACB từ tài liệu gốc trước khi mở P/B, và nguồn lịch sử đầu 2016.

- [x] Tách kiểm tra giá mới nhất cho định giá khỏi mẫu lịch sử; UI/PDF, cảnh báo và thống kê chuỗi đồng bộ; 88 kiểm thử đạt.

## Sửa theo phản hồi bố cục, HNX/UPCoM, khuyến nghị (11/10/2026)

- [x] Đối chiếu mẫu CFO; chuyển toàn bộ các phần phân tích sang frame cố định chữ bên phải, biểu đồ/bảng tóm tắt bên trái. Phụ lục toàn chiều rộng.
- [x] Thêm Vietcap dự phòng cả chuỗi và đối chiếu bằng nhà cung cấp khác; kiểm tra mã/mảng/giá/ngày, lưu snapshot và tham số POST.
- [x] Đệm ngày kết thúc KBS và lọc lại ngày chốt, không dùng phiên tương lai/hiện tại.
- [x] Cho phép ba Head khi Value4 trống, giữ chặn ánh xạ không rõ/24 tháng; bổ sung CFO chứng khoán 4735.
- [x] Khuyến nghị nghiên cứu, mức tin cậy, kỳ/horizon và quy tắc công khai; luận điểm có bằng chứng/nguồn/điều kiện xác nhận/bác bỏ.
- [x] 101 tests đạt; nguồn thực sáu mã gồm HNX/UPCoM; UI AppTest SHS/VNZ từ kết quả thực không ngoại lệ; render tất cả trang ba PDF mới.
- [x] SHS: tự đọc bảng kiểm toán riêng lẻ 2025 trong BCTN, kiểm tra cột/đơn vị/phạm vi/ngày/cân đối; khớp 12 giá trị với KBS, không sửa kỳ KBS lỗi.
- [x] Cache có checksum/URL/thời gian; Yahoo lỗi chỉ lưu lần thử nếu nguồn dự phòng thành công; thống kê đóng cửa nguồn có nhãn điều chỉnh quyền.
- [x] SHS THEO DÕI với luận điểm cho vay/ROE và rủi ro lợi nhuận chưa thực hiện; 112 tests, pipeline thực, AppTest và 14 trang PDF cuối đã kiểm tra. Minh chứng: submission/evidence/shs_issuer_upgrade.json.
- [ ] Xác minh kỳ 2025 F88, bổ sung QNS/mẫu peer F88. Không thay metadata lỗi hoặc NCI null bằng giả định số liệu.
- [x] Bổ sung vnstock 4.0.8 (dòng thư viện trước gọi vnstock3): dự phòng giá KBS/VCI sau HTTP, kiểm tra đơn vị/ngày/schema và lỗi SDK, loại cùng nguồn gốc khi đối chiếu; 119 tests và sáu kết nối thực SHS/VNZ/F88 đều khớp 20/20 phiên.

Minh chứng: submission/exchange_report_acceptance.json; phương pháp và giới hạn: docs/exchange_report_upgrade.md. Đây là kiểm chứng sáu mã, không phải toàn thị trường; API Gemini thật và deploy vẫn chưa được kiểm chứng.

## Close và vnfinancialdata (11/10/2026)

- [x] Biểu đồ/MA/định giá dùng Close; thống kê Adj Close tách riêng với nhãn mức kiểm chứng.
- [x] Tự lấy SDK vnfinancialdata 0.1.2, ba bảng HSX/HNX, kiểm tra SHA/schema/đơn vị/ánh xạ, xuất CSV đầy đủ và tích hợp UI/PDF.
- [x] Chẩn đoán rõ kỳ chính, metadata KBS bị loại, chỉ tiêu thiếu và phương pháp không áp dụng.
- [x] 134 kiểm thử offline đạt; SHS/VNM chạy nguồn thực, BCTC đến 2025, minh chứng riêng trong submission/evidence/*_close_vnfinancialdata.json.
- [x] AppTest chọn năm/tải CSV không ngoại lệ; PDF bật/tắt phần bổ sung đúng; xem toàn bộ 29 trang hai PDF và khởi động lại web bằng .venv.
- [ ] Xác minh phạm vi/ngày công bố từng kỳ dataset trước khi dùng tự thay dữ liệu chính; bổ sung nguồn UPCoM có metadata phù hợp.

## Báo cáo đầu tư, mẫu định giá và SOTP (11/10/2026)

- [x] Định giá chính theo P/E/P/B trung vị mẫu đồng kỳ; so sánh bội số hiện tại, ROE/tăng trưởng/đòn bẩy; ưu tiên phương pháp theo loại ngành.
- [x] Tách giả định nhập tay/Gordon/DCF/bình quân vào phụ lục độ nhạy; khuyến nghị chỉ dùng phương pháp chính đủ dữ liệu.
- [x] Tự lấy VN-Index/Brent, bài công khai VnExpress/VnEconomy, lưu ngày/URL/hash; luận điểm có bằng chứng, kênh tác động và chỉ tiêu theo dõi.
- [x] Gemini nhận nội dung bài có giới hạn và số liệu; chặn số tự tạo/dẫn nguồn không hợp lệ/diễn giải quá dài, fallback.
- [x] Engine SOTP kiểm tra mảng/cầu nối/số CP; adapter REE/SSI tự lấy báo cáo và giữ tham khảo cũ ngoài khuyến nghị.
- [x] 155 tests đạt; pipeline nguồn thực SHS/VNM/REE và minh chứng riêng. Chi tiết docs/investment_research_upgrade.md.
- [x] AppTest ba mã thực; PDF đầy đủ/tóm tắt/bỏ mục; render 53 trang cuối, rà soát các phần và phân trang; web health HTTP 200.
- [ ] Xác minh BCTC REE 2025 và tài sản từng mảng SOTP mới; thêm adapter doanh nghiệp khác có đủ nguồn; kiểm chứng API Gemini/Cloud thật.

## Cập nhật SSI và chất lượng báo cáo (11/10/2026)

- [x] SSI dùng PDF kiểm toán hợp nhất 2025 chính thức, ngày 27/03/2026, kiểm tra năm/phạm vi/VND/hàng/cân đối/lợi nhuận; khớp 12 giá trị cột năm KBS. Không sửa metadata nguồn sai; cột 2024 giữ số trình bày lại.
- [x] TVS có adapter PDF kiểm toán và 12 giá trị đối chiếu; SSI có mẫu VDS/TVS cùng BCTC 2025, P/E/P/B từ giá/CP snapshot, không phải trung bình toàn ngành hoặc TTM.
- [x] Tăng chỉ tiêu so sánh phù hợp ngành, chẩn đoán lý do loại peer; nến OHLC/volume/MA và lọc khoảng nhìn trên web.
- [x] Tin vĩ mô/ngành gộp một ô mỗi mục, tối đa tám bài phù hợp/phạm vi, preview ba bài có nút mở/thu gọn; gộp kênh vĩ mô vào ngành.
- [x] Gemini gắn source IDs từ evidence IDs, giữ từng nhận xét hợp lệ, chẩn đoán lỗi riêng/JSON; không xuất khóa hoặc SDK error nhạy cảm.
- [x] PDF nguồn theo tên đơn vị, biểu đồ/nhãn dễ đọc hơn, loại biểu đồ giá lặp tại tổng quan; kiểm tra toàn bộ trang. OCR Cloud có packages.txt; chưa triển khai Cloud.
- [ ] SSI BCTC quý/bán niên 2026 và TTM chưa tích hợp; mẫu định giá SSI hiện chỉ hai doanh nghiệp đủ điều kiện.
- [x] Người dùng cho phép gửi bằng chứng SSI tới Google; khóa Secrets đọc được thông tin model. Hai lần tạo nhận xét thật trả HTTP 504/503, không có nhận xét để xuất; minh chứng `submission/evidence/ssi_gemini_live.json`.
- [ ] Xác nhận một phản hồi Gemini thật hợp lệ và xuất PDF có AI khi dịch vụ hoạt động; Streamlit Cloud chưa triển khai/kiểm chứng.

Chi tiết và minh chứng: docs/ssi_report_upgrade.md; submission/evidence/ssi_report_upgrade.json.

Kiểm chứng cuối: 171 kiểm thử offline đạt; AppTest SSI hiển thị lỗi HTTP 503, giữ nút tải PDF và không ngoại lệ (API/PDF được giả lập trong AppTest). PDF SSI 17 trang và hồi quy SHS/VNM/REE đã kiểm tra ở đợt trước; PDF được giữ nguyên vì chưa có nhận xét AI thật.

## Giao diện theo mẫu Pinterest

- [x] Truy cập pin và xem ảnh mẫu Credix; phân tích bố cục, màu, chữ và khung dashboard.
- [x] Nền trời xanh/mây tự tạo, tiêu đề giữa trang, CTA cuộn tới phần nhập mã, khung bo tròn và thẻ xanh tím nhạt; assets lưu trong dự án.
- [x] Bố cục cho điện thoại, trạng thái focus bàn phím và chế độ giảm chuyển động.
- [x] Hồi quy AppTest SSI: không ngoại lệ, tin 3 → 8 → 3, tin doanh nghiệp 12 bài, lọc biểu đồ; một lượt pipeline.

Chi tiết và minh chứng: docs/pinterest_ui_design.md; submission/evidence/pinterest_ui_upgrade.json.

Cập nhật 12/10/2026: môi trường .venv mới được cài lại theo requirements. PyPI đang cách ly vnstock, nên bỏ gói khỏi cài đặt bắt buộc; giữ adapter tùy chọn và kết nối HTTP Yahoo/KBS/Vietcap, vnfinancialdata. Chi tiết: docs/vnstock_fallback.md.

Kiểm tra lại 12/10/2026 trên .venv mới: cài requirements thành công, pip check không xung đột, 171 kiểm thử đạt. AppTest giao diện đạt; Chrome 1440px/390px không tràn ngang, nút bắt đầu cuộn đúng vị trí. Web chính khởi động tại localhost:8501. Ảnh desktop/mobile được cập nhật; ảnh kết quả SSI giữ từ lượt kiểm tra 11/10 với dữ liệu đã lưu.

## MBB và mẫu ngân hàng (12/10/2026)

- [x] Tự tải/đọc PDF MBB hợp nhất kiểm toán 2025, đối chiếu chín chỉ tiêu; giữ nguyên việc loại metadata KBS 24 tháng.
- [x] MBB bán niên soát xét 2026: kiểm tra OCR, cân đối, phân bổ LNST và cột đầu năm; phân biệt số dư với luồng sáu tháng trên UI/PDF.
- [x] CTG/TCB 2025 từ PDF website ngân hàng; so sánh tài chính cùng kỳ với CTG/TCB/ACB/VIB. P/B hai mã có vốn mẹ, P/E bốn mã.
- [x] Bổ sung luận điểm bán niên và bằng chứng cho Gemini tùy chọn; giữ điều kiện khuyến nghị, không nhân đôi lợi nhuận hoặc ghép TTM.
- [x] Kiểm chứng nguồn thật MBB: phân tích năm 2025, bán niên 30/06/2026, giá khớp 20/20 phiên, THEO DÕI với P/B chênh +1,53%; PDF 20 trang và AppTest đạt.
- [ ] Mẫu định giá TTM/P/B bán niên đồng kỳ và mở rộng PDF ngân hàng ngoài cấu hình hiện tại; TTM và tỷ lệ MBB đã bổ sung ở đợt tiếp bên dưới.

Chi tiết: docs/mbb_bank_upgrade.md; submission/evidence/mbb_upgrade/acceptance.json. Ngày khả dụng PDF mới là 12/10/2026, chưa xác nhận ngày công bố danh mục; truy vấn trước ngày này không được sử dụng các tài liệu mới.

Kiểm chứng cuối: 189 kiểm thử offline đạt (18 kiểm thử ngân hàng mới); AppTest MBB không ngoại lệ, web 8501 trả health OK.

## TTM và NIM/NPL/CAR MBB (đợt tiếp 12/10/2026)

- [x] Tự đọc NIM/CAR hợp nhất năm 2025, xác nhận tỷ lệ và phạm vi bằng bảng/nhận xét trong PDF gốc có checksum.
- [x] NPL tính lại từ nhóm 3–5 và tổng cho vay gộp thuyết minh 9.1; các nhóm và margin/ứng trước cộng khớp cả hai cột, đối chiếu tỷ lệ công bố trong sai số làm tròn.
- [x] Ghép TTM bằng năm + bán niên − cùng kỳ; khóa kỳ, ngày, đơn vị, phạm vi, khả dụng, phân bổ mẹ/NCI và giữ ba toán hạng có nguồn.
- [x] P/E TTM vốn hóa/LNST mẹ hiển thị riêng; không trộn với trung vị P/E năm hoặc ép khuyến nghị mua.
- [x] Bảng TTM/tỷ lệ trên web/PDF, bằng chứng cho Gemini tùy chọn và cảnh báo thiếu theo dữ liệu thực tế.
- [x] TCB NCI trong ngoặc được hiểu theo quy ước khấu trừ của bản gốc; số âm NCI thực tế ở tài liệu khác vẫn được giữ.
- [ ] Mẫu P/E TTM/P/B bán niên đồng kỳ; tỷ lệ kỳ 2026 và bộ đọc cho mọi ngân hàng.

Phương pháp và nguồn: docs/mbb_metrics_upgrade.md. Minh chứng đợt mới: submission/evidence/mbb_metrics_upgrade/.

- [x] 202 kiểm thử đạt; chạy nguồn thật MBB và kiểm tra các toán hạng/nguồn TTM, NPL/NIM/CAR.
- [x] AppTest không ngoại lệ, bảng tỷ lệ/TTM/P/E TTM có trên UI, bảy nút tải; PDF 20 trang và tóm tắt có các mục mới, kiểm tra render.

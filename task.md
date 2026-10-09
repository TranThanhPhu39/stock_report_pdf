# Task — StockInsight

Cập nhật 09/10/2026. Các yêu cầu chính đã có luồng chạy thực; không coi đề xuất mở rộng là điều kiện bắt buộc của đề gốc.

## Đã hoàn thành

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

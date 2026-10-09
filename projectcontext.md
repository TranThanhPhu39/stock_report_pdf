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

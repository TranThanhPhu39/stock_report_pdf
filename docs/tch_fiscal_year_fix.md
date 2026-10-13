# TCH: dữ liệu tài chính theo niên độ riêng

Kiểm tra ngày 13/10/2026 bắt đầu từ lượt người dùng `TCH_20261013_145956_980502`.

## Nguyên nhân

- KBS trả metadata năm 2026 và 2025 cùng `ID=1`. Các cột giá trị còn bị lặp; ngày đầu/cuối ở một số head không khớp niên độ thực. Bộ đọc từ chối bộ này là cần thiết, không được tự gán lại các cột theo thứ tự.
- TCH có niên độ 01/04–31/03. BCTC kiểm toán gọi là năm 2025 kết thúc ngày 31/03/2026. Không ghép với mẫu ngành kết thúc 31/12/2025.
- Vietcap trả `ticker=TCH`, `organCode=HHSF`. `organCode` là định danh nội bộ, không phải mã giao dịch. Code cũ yêu cầu hai trường bằng nhau, làm mất các quý hợp lệ.
- HTTP 503 Gemini là lỗi dịch vụ cho lần gọi AI; không phải nguyên nhân tài chính KBS bị loại.

## Thay đổi

- Thêm `src/data/tch_issuer.py` và bản chép có nguồn `config/issuer_snapshots/TCH_2025.json`. Các số đã được kiểm tra trực quan từ PDF kiểm toán hợp nhất chính thức, trang PDF 7–11. Chỉ chấp nhận khi PDF tải từ doanh nghiệp khớp chính xác SHA256 `95dfa0d407102dc1d253edef5ef1fa0efc56fa3eb265a2907dd63eef4390903d` và trang công bố khớp ngày/niên độ. File khác hoặc công bố sau ngày phân tích đều bị loại.
- Hai cột năm 2025/2024 giữ ngày kết thúc 31/03/2026 và 31/03/2025; kiểm tra cân đối tài sản/nợ/vốn và phân bổ lợi nhuận ở cả hai cột. Không tự gọi bản chép này là đối chiếu nguồn độc lập.
- Cho phép `organCode` khác ticker khi các quý cùng định danh nội bộ; vẫn từ chối ticker sai hoặc định danh không nhất quán. Dữ liệu quý theo kỳ lịch của Vietcap được trình bày riêng; không lấy nhãn quý nguồn làm quý niên độ TCH.
- Thông báo tài chính có ngày cuối kỳ; TTM niên độ riêng ghi rõ đã có BCTC năm nhưng chưa hỗ trợ ghép cập nhật lũy kế/cùng kỳ. Rút gọn câu chặn định giá để tránh lặp cùng lý do.

## Kiểm chứng và giới hạn

Lượt mạng thật `TCH_20261013_152215_296940` đọc hai kỳ năm và 34 kỳ quý. Doanh thu năm tài chính 2025 là 1.447.394.456.840 VND, LNST hợp nhất 259.196.467.437 VND, LNST mẹ 211.060.969.763 VND; giá cuối chuỗi 12/10/2026. Đây là dữ liệu kỳ, không phải dự báo.

Streamlit AppTest với kết quả lưu chạy không exception, có tám tab và không còn câu “Chưa có kỳ tài chính hợp lệ”. PDF kiểm tra được render chín trang, đã kiểm tra nhãn hợp nhất. Bộ kiểm thử toàn dự án cuối cùng đạt **239 kiểm thử**.

Phân tích vẫn ở trạng thái `partial`: chưa đủ mẫu ngành đúng kỳ và nguồn độc lập để định giá chính. Nhãn “CHƯA ĐỦ CƠ SỞ KHUYẾN NGHỊ” vì vậy vẫn có thể đúng. TTM niên độ 01/04–31/03 chưa có bộ đọc lũy kế đã xác minh. Bản chép chỉ hỗ trợ đúng phiên bản PDF/niên độ đã nêu, không tự đọc mọi báo cáo TCH mới; thay đổi file cần kiểm tra và cập nhật bản chép có nguồn.

Nguồn: [công bố kiểm toán TCH năm 2025](https://www.hoanghuy.vn/bao-cao-tai-chinh/tch-bao-cao-tai-chinh-nam-2025-da-kiem-toan-giai-doan-01042025-31032026/), [PDF hợp nhất](https://www.hoanghuy.vn/images/uploadfiles/20260625%20-%20tch%20-%20bao%20cao%20tai%20chinh%202025%20hop%20nhat.pdf).

## Bổ sung P/B tham khảo gần kỳ

Lượt `TCH_20261013_155155_291761` kiểm tra phần định giá còn thiếu:

- Sửa lỗi kỳ mẫu: khi thử năm cũ vẫn không đủ hai peer, không hiển thị năm cũ như một mẫu chung đã chọn. Định giá chính vẫn yêu cầu đúng kỳ, phạm vi và ngày giá.
- Sửa lấy giá peer: Yahoo trả thành công nhưng thiếu đúng ngày yêu cầu cũng phải thử Vietcap, không chỉ chuyển nguồn khi HTTP lỗi. Giá vẫn phải khớp KBS trong dung sai hiện có.
- Thêm `src/data/near_period_pb.py`: chỉ dành cho doanh nghiệp phi tài chính có niên độ riêng khi chưa có định giá chính. Chọn tối đa bốn mã cùng nhóm nguồn, lớn nhất theo tài sản trong các snapshot của chính lượt chạy. Yêu cầu vốn cổ đông mẹ dương, cùng phạm vi/loại báo cáo, cân đối tài sản/nợ/vốn, số dư trước ngày cuối kỳ mã phân tích không quá **90 ngày**, giá cùng ngày và CP cùng ngày chốt. Ngưỡng 90 ngày là chính sách tham khảo của ứng dụng, không phải chuẩn kế toán hay bảo đảm khả năng so sánh.
- Không tạo P/E từ mẫu lệch kỳ, không ghép lợi nhuận/TTM khác niên độ, không đưa giá tham khảo vào `valuation.primary`, khuyến nghị hoặc điều kiện tích lũy. Không thay mẫu ngành đồng kỳ hiện có.
- Giao diện có nhãn riêng **Giá tham khảo P/B gần kỳ** và **Chênh lệch tham khảo** khi đủ mẫu. Tab Định giá/PDF liệt kê từng mã, ngày vốn mẹ, độ lệch và P/B. Không gọi giá này là giá mục tiêu hoặc RNAV. Vốn sổ sách chưa đánh giá lại dự án/đất, pháp lý, dòng tiền; cơ cấu tài sản và hiệu quả vốn giữa các mã có thể khác nhiều.

Lượt thật có VHM, KSF, DXG và SIP: số dư 31/12/2025, lệch TCH 90 ngày, giá 12/10/2026. Trung vị P/B **2,2583294517** × BVPS mẹ TCH cho tham khảo **25.875,97 VND/CP**. Đây chỉ là kết quả công thức của mẫu này; chênh lệch lớn không tự chứng minh TCH bị định giá thấp. Định giá chính vẫn thiếu cơ sở, mức tin cậy vẫn thấp.

AppTest xác nhận nhãn tham khảo hiển thị, bốn peer và tám tab, không exception. PDF kiểm tra chín trang, phần bảng tham khảo đã render và kiểm tra trực quan. **244 kiểm thử cuối đều đạt**, gồm hồi quy giới hạn ngày/phạm vi/NCI, giá dự phòng, kỳ mẫu thất bại và cách ly giá tham khảo khỏi định giá chính.

Tham khảo về phương pháp và giới hạn bội số: [CFA Institute — Market-Based Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples). Chính sách ngày/nguồn cụ thể ở trên là thiết kế của ứng dụng.

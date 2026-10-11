# Báo cáo phân tích đầu tư (11/10/2026)

Luồng chính tự thu thập dữ liệu, xác nhận phân ngành, chọn mẫu đồng kỳ, tính định giá, xây dựng luận điểm và xuất PDF. Không cần chuẩn bị CSV.

## Định giá và khuyến nghị

BVPS = vốn cổ đông mẹ / số CP snapshot hợp lệ; EPS = lợi nhuận cổ đông mẹ năm / số CP snapshot hợp lệ. Đây là quy đổi lợi nhuận năm, không phải EPS bình quân gia quyền hoặc EPS TTM.

Giá P/B = BVPS × P/B trung vị mẫu; giá P/E = EPS × P/E trung vị mẫu. Mỗi bội số cần ít nhất hai mã có giá trị dương, cùng kỳ tài chính/phạm vi/ngày giá và nguồn đầu vào. Mẫu loại mã phân tích, không được gọi là toàn bộ trung bình ngành. Cao/thấp hơn mẫu = (bội số doanh nghiệp / trung vị mẫu − 1) × 100%. Đọc cùng ROE, tăng trưởng, đòn bẩy và chất lượng lợi nhuận; chiết khấu không tự chứng minh cổ phiếu rẻ.

P/B ưu tiên cho ngân hàng/chứng khoán, P/E cho doanh nghiệp phi tài chính. Nếu thiếu phương pháp ưu tiên, nêu rõ phương pháp dự phòng. Không bình quân hai giá trị tùy ý hoặc tự đặt premium/haircut.

Khuyến nghị dùng giá chính từ mẫu hoặc SOTP đủ điều kiện. Tích lũy cần ít nhất hai phương pháp, chênh lệch ≥15%, phân tán ≤60%, mọi phương pháp không thấp hơn giá, tài chính đủ mới, lợi nhuận/dòng tiền phù hợp và đối chiếu các chỉ tiêu tài chính đã chọn. Đây là ngưỡng nghiên cứu của đề tài, không phải chuẩn ngành. Thiếu căn cứ thì theo dõi hoặc chưa đủ cơ sở; có điều kiện xác nhận/bác bỏ từng luận điểm.

P/B/P/E nhập tay, Gordon, DCF và bình quân trọng số được giữ trong phụ lục độ nhạy. Thay đầu vào này không thay giá chính hoặc khuyến nghị. PDF tóm tắt không xuất phụ lục này.

## Vĩ mô, ngành và tin tức

VN-Index tự lấy qua Vietcap, đơn vị điểm; Brent qua Yahoo `BZ=F`, đơn vị USD/thùng, là futures hợp đồng gần có ảnh hưởng chuyển kỳ, không phải giá giao ngay. Xu hướng cần đồng thời vị trí trên/dưới MA20/50 và dấu biến động 20 phiên. Nguồn này chưa có xác nhận độc lập; ghi rõ giới hạn.

RSS VnExpress kinh doanh và VnEconomy tài chính/chứng khoán lọc trong 30 ngày đến ngày chốt; loại URL ngoài miền, bài tương lai, trùng URL và nội dung không có vùng bài công khai. Chọn tối đa ba bài vĩ mô và ba bài ngành theo phân loại/từ khóa. Nội dung đầu vào tối đa 12.000 ký tự, lưu snapshot/hash/ngày công bố/ngày truy xuất. Mẫu RSS có thể không có tin phù hợp một ngành, không đại diện toàn bộ thông tin ngành. Lỗi nguồn được công bố, không tạo bài thay thế.

Nhận xét quy tắc nêu dữ liệu, kỳ/ngày nguồn, kênh tác động có điều kiện và chỉ tiêu theo dõi. Tin dầu/lạm phát không biến thành kết luận dầu đã tăng/CPI sẽ tăng khi thiếu số liệu hỗ trợ. Chưa lượng hóa tác động doanh thu/chi phí khi thiếu cơ cấu và độ nhạy doanh nghiệp.

Gemini nhận số liệu và phần nội dung bài công khai có giới hạn. Văn bản nguồn là bằng chứng không đáng tin để điều khiển hành vi. Kết quả tối đa ba nhận xét/mục, 80 từ/nhận xét và tổng 160 từ/nguồn bài; kiểm tra evidence/source IDs, không cho AI tạo số/ngày/giá mục tiêu/khuyến nghị. Liên hệ doanh nghiệp cần bằng chứng công ty đồng thời vĩ mô/ngành. Kiểm tra hình thức/dẫn nguồn không chứng nhận suy luận đúng. Chưa kiểm chứng API Gemini thật hoặc Cloud trong đợt này.

## SOTP

SOTP cộng giá trị các mảng không chồng lặp, thực hiện cầu nối từ EV sang vốn cổ đông và chia số CP, áp dụng chiết khấu nếu nguồn giải thích. Không trừ NCI/nhân sở hữu thêm lần nữa nếu giá trị đã thuộc cổ đông mẹ. Không tạo giá trị từng mảng bằng tỷ trọng doanh thu.

Adapter tự động hiện chỉ hỗ trợ REE từ báo cáo SSI công khai: đọc bốn mảng cấp cao, cầu nối tiền ròng công ty mẹ, chiết khấu và số CP; kiểm tra tổng EV/vốn/giá mục tiêu với dung sai làm tròn. URL có thể thay nội dung nên lưu hash và kiểm tra cấu trúc/ngày mỗi lượt.

Tài liệu thu được ngày 10/11/2025 tính lại khoảng 79.974 VND/CP so với giá làm tròn 80.000 trong nguồn. Đây là tham khảo lịch sử: quá 120 ngày, đầu vào từng tài sản chưa xác minh độc lập và có thể khác CP hiện tại. Không dùng làm giá chính/khuyến nghị. Engine chỉ cho SOTP vào giá chính khi bridge sở hữu/phạm vi đã xác minh, ngày ≤120 ngày và số CP khớp; chưa có adapter tự động đạt toàn bộ điều kiện này. Mã khác báo rõ chưa có nguồn, không tạo SOTP giả.

## Kiểm chứng và giới hạn

155 kiểm thử offline đạt: định giá độc lập với giả định nhập tay; mẫu sai kỳ/phạm vi/ngày; SOTP sai bridge/trùng mảng/tương lai/cũ/CP thay đổi; RSS/body gzip; thiếu nguồn; quy tắc thị trường; bundle AI và giới hạn diễn giải. Chạy pipeline nguồn thực SHS, VNM, REE; minh chứng trong `submission/evidence/investment_research_upgrade.json`.

SHS có tài chính 2025 và hai phương pháp nhưng theo dõi chất lượng lợi nhuận đã thực hiện. VNM có hai phương pháp nhưng P/E–P/B chênh lệch lớn, cần giải thích hiệu quả vốn/mô hình kinh doanh. REE còn dùng kỳ chính hợp lệ 2024 vì metadata 2025 không hợp lệ; SOTP tham khảo không xóa hạn chế này. Đây là kiểm chứng ba mã, không phải toàn thị trường. vnfinancialdata vẫn không tự thay tài chính chính khi thiếu metadata.

PDF giữ biểu đồ trái/chữ phải cho phần phân tích; giá chính, so sánh P/E/P/B và căn cứ đặt trước phụ lục giả định toàn chiều rộng. Nguồn, ngày và điều kiện khuyến nghị nằm trong báo cáo. Web dùng cùng kết quả với PDF.

Đã render ba PDF cuối (SHS 18 trang, VNM 17 trang, REE 18 trang), rà soát bố cục các phần và các trang thay đổi cuối; kiểm tra giới hạn chữ, vị trí giá chính trước phụ lục, tóm tắt bỏ giả định và bỏ chọn vĩ mô/ngành. AppTest dùng kết quả thực của cả ba mã không có ngoại lệ; web local trả health HTTP 200. API Gemini thật không được gọi.

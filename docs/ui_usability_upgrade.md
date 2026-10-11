# Cập nhật giao diện (11/10/2026)

Phần mẫu so sánh trước đây dùng `st.json` nên hiển thị cấu trúc dữ liệu nội bộ. Thay bằng số doanh nghiệp cùng nhóm, số đủ điều kiện, các mã được chọn và bảng lý do chưa đưa vào mẫu bằng tiếng Việt. Giải thích riêng phạm vi danh mục phân ngành của nguồn; mã không được chọn vì giới hạn mẫu khác với mã bị loại do thiếu dữ liệu.

Kết quả có khuyến nghị và ba số liệu chính ở đầu. Dùng một nhóm tab: Tổng quan, Vĩ mô, Ngành, Tài chính, Định giá, Cơ hội và rủi ro, Tin tức, Nguồn dữ liệu. Các giả định nhập tay gom vào một mục không bắt buộc; dữ liệu bổ sung và nhận xét chi tiết mặc định thu gọn. Các bảng kịch bản, SOTP, đối chiếu và công thức dùng nhãn tiếng Việt thay trường JSON. Điều kiện dữ liệu ảnh hưởng phân tích vẫn hiện ở mục tương ứng.

Tin tức trước và sau phân tích dùng chung giao diện: sắp tin mới nhất trước, loại trùng, mặc định tối đa 3 tin, nút Xem tất cả và Thu gọn còn 3 tin. Chỉ hiện nút khi có hơn 3 tin. Phạm vi tin doanh nghiệp và mẫu cùng ngành có trạng thái mở riêng. Nút không chạy lại pipeline hoặc tạo lại PDF. Khi bắt đầu phân tích mới, danh sách kết quả trở về trạng thái 3 tin. Bấm tiêu đề mở bài gốc. Không giảm số tin lưu trong kết quả hoặc PDF.

Kiểm tra bằng Streamlit AppTest với kết quả SHS/VNM/REE đã lưu, mô phỏng nguồn tin cho màn hình ban đầu: mở/thu gọn, đổi phạm vi, nguồn không có tin, không có JSON trên giao diện, pipeline chỉ được gọi một lần sau các thao tác tin. Minh chứng: `submission/evidence/ui_usability_upgrade.json`. Endpoint Streamlit đang chạy trả `ok`. Chưa kiểm tra ảnh hiển thị trên trình duyệt vì phiên làm việc không có trình duyệt khả dụng; cách xuống dòng của tab trên màn hình nhỏ cần được xem thực tế. Không thay đổi tính toán, dữ liệu hay nội dung PDF; không đọc hoặc sửa API key.

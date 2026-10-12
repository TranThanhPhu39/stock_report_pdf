# Giao diện StockInsight theo mẫu Pinterest

Tham khảo [ảnh poster Credix trong pin người dùng gửi](https://www.pinterest.com/pin/54958057951233737/) và [trang giới thiệu mẫu Credix](https://webflow.com/templates/html/credix-website-template). Phân tích dựa trên hình đã xem; chưa rà soát toàn bộ video chuyển động của mẫu.

## Những nét chính của hình mẫu

Nền trời xanh với mây mềm tạo chiều sâu. Thanh điều hướng nhỏ ở trên, thông điệp lớn nằm giữa và nút hành động hình viên thuốc tạo điểm bắt đầu rõ ràng. Dashboard trắng trong nhẹ nổi phía trước nền; góc bo tròn, đường viền sáng, bóng đổ mềm. Các thẻ nội dung xanh tím nhạt chia thông tin thành cụm, có nhiều khoảng trống. Chữ sans serif và bảng màu nhất quán tạo cảm giác nhẹ, hiện đại.

## Áp dụng vào sản phẩm

| Thành phần mẫu | StockInsight |
| --- | --- |
| Tiêu đề giữa nền trời | “Hiểu thị trường. Tự tin quyết định.” và mô tả mục đích báo cáo |
| Nút hành động nổi bật | “Bắt đầu phân tích” cuộn tới phần nhập mã |
| Dashboard nổi | Khung chọn cổ phiếu, ngày, nội dung PDF và Gemini |
| Thẻ xanh tím nhạt | Tóm tắt báo cáo được chọn và các chỉ tiêu kết quả |
| Nội dung theo cụm | Các tab vĩ mô, ngành, tài chính, định giá và tin tức |
| Chuyển động nhẹ | Hiệu ứng xuất hiện tiêu đề; tôn trọng chế độ giảm chuyển động |

Nền mây là SVG tự tạo trong `assets/ui/sky.svg`; CSS nằm trong `assets/ui/theme.css`, được nạp qua `src/ui/theme.py`. Không dùng ảnh chụp mẫu làm nền sản phẩm hoặc đưa mã template Credix vào dự án. Giao diện không cần tải font, ảnh hay thư viện thiết kế từ bên thứ ba khi chạy.

Phần chọn mã và ngày xếp dọc trên điện thoại; khung, tab và tin tức điều chỉnh khoảng cách theo chiều rộng. Các liên kết điều hướng và nút có trạng thái focus để dùng bàn phím. Biểu đồ nến vẫn dùng xanh/đỏ để phân biệt phiên tăng/giảm.

## Kiểm chứng và phạm vi

AppTest dùng kết quả SSI đã thu thập, giả lập pipeline và xuất PDF: không ngoại lệ; tin vĩ mô/ngành 3 → 8 → 3, tin doanh nghiệp mở đủ 12 bài, bộ lọc biểu đồ hoạt động; chỉ một lượt phân tích. Dữ liệu, phương pháp định giá và nội dung PDF không được thay đổi bởi đợt giao diện này.

Minh chứng bố cục trên trình duyệt và kiểm tra chức năng được lưu trong `submission/evidence/pinterest_ui_upgrade.json`. Kiểm tra kết quả trong trình duyệt dùng máy chủ xem thử riêng với dữ liệu SSI đã lưu; ứng dụng chính vẫn ở cổng 8501 và tự lấy dữ liệu khi người dùng phân tích.

Kiểm tra lại 12/10/2026 trên .venv mới: cài requirements thành công, pip check không xung đột, 171 kiểm thử đạt. AppTest giao diện đạt; Chrome 1440px/390px không tràn ngang, nút bắt đầu cuộn đúng vị trí. Web chính khởi động tại localhost:8501. Ảnh desktop/mobile được cập nhật; ảnh kết quả SSI giữ từ lượt kiểm tra 11/10 với dữ liệu đã lưu.

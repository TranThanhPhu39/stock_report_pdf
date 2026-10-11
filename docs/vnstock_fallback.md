# Kết nối vnstock bổ sung (11/10/2026)

Theo yêu cầu người dùng, bổ sung thư viện vnstock vào luồng tự lấy giá cuối ngày. Máy hiện dùng bản `vnstock==4.0.8`; tên `vnstock3` là dòng cũ đã hợp nhất sang vnstock. Cố định phiên bản trong requirements để đơn vị và schema không thay đổi âm thầm.

## Luồng lấy và đối chiếu

1. Yahoo Finance.
2. KBS HTTP trực tiếp.
3. Vietcap HTTP trực tiếp.
4. Component Quote KBS của vnstock.
5. Component Quote VCI của vnstock.

Chỉ chuyển tiếp khi tải/schema/kiểm tra OHLCV thất bại, chọn nguyên chuỗi của kết nối đầu tiên hợp lệ. Không ghép lịch sử khác nguồn. Thiếu đầu kỳ được cảnh báo; bản này chưa thay chính sách để tải mọi nguồn và chọn lịch sử dài nhất.

KBS trực tiếp và vnstock–KBS thuộc cùng một nguồn gốc. Vietcap trực tiếp và vnstock–VCI cũng thuộc cùng một nguồn gốc. Hàm `price_source_family` xác định nhóm này; bộ đối chiếu tự loại các kết nối cùng nhóm với giá chính. Ví dụ giá chính vnstock–KBS chỉ có thể đối chiếu bằng Yahoo hoặc Vietcap/VCI. Chỉ thành công khi có giá nguồn khác đúng ngày, sai lệch trong 0,1%; một mình thư viện không mở khóa khuyến nghị/định giá.

## Hợp đồng dữ liệu

- Quote component giữ metadata mã và nhà cung cấp; adapter hợp nhất Quote của 4.0.8 có thể mất metadata VCI khi cắt DataFrame, nên ứng dụng sử dụng component nguồn trực tiếp trong thư viện.
- Giá cổ phiếu trả qua thư viện là nghìn VND/cổ phiếu. Bộ chuyển đổi nhân đúng 1.000 theo phiên bản đã đọc mã nguồn, giữ khối lượng nguyên đơn vị cổ phiếu. Không suy đoán hệ số theo độ lớn giá hoặc sửa để khớp nguồn thứ hai.
- Kiểm tra mã, nguồn, loại tài sản, schema, giá hữu hạn/dương, OHLC, khối lượng, ngày trùng và ngày chốt UTC+7. Không dùng phiên hiện tại/tương lai, không làm tròn khối lượng lẻ thành cổ phiếu hợp lệ.
- KBS đệm ngày kết thúc hai ngày để tránh bỏ phiên cuối; lọc lại <= ngày chốt. VCI dùng ngày chốt. Kết nối VCI của thư viện có bước làm tròn giá; khớp 20 phiên không chứng nhận độ chính xác toàn lịch sử.
- Không tự đặt Close thành Adj Close. Điều chỉnh cổ tức/chia tách/quyền vẫn chưa được xác minh.
- Snapshot ghi rõ `vnstock_library_output_not_raw_http`: đây là đầu ra thư viện, không phải body HTTP gốc. Lưu phiên bản, nguồn gốc, tham số, đơn vị đầu vào và hệ số. Những lỗi thử nguồn lưu trong acquisition.json.
- Import vnstock bị tắt chức năng tự viết AGENTS.md và cấu hình agent toàn máy. Chỉ dùng chức năng dữ liệu; không gọi đăng ký key hoặc cài gói sponsor.
- Thiếu thư viện, phiên bản khác hợp đồng, lỗi SDK/API hoặc SDK SystemExit đều trở thành lỗi nguồn, giữ ứng dụng hoạt động và thử kết nối tiếp theo.

## Kiểm chứng và phạm vi

119 kiểm thử offline đạt, gồm bảy kiểm thử mới cho đơn vị/ngày/metadata, lỗi SDK, kết nối thứ tư/thứ năm và việc loại nguồn gốc trùng khi đối chiếu.

Kiểm tra thực khoảng 11/10/2025–11/10/2026 (phiên cuối 09/10/2026):

| Mã | vnstock–KBS | vnstock–VCI | Giá cuối (VND) | Đối chiếu mỗi kết nối |
|---|---:|---:|---:|---|
| SHS | 247 phiên | 247 phiên | 11.700 | 20/20 khớp |
| VNZ | 235 phiên | 235 phiên | 533.000 | 20/20 khớp |
| F88 | 247 phiên | 247 phiên | 46.900 | 20/20 khớp |

Minh chứng: `submission/evidence/vnstock_fallback.json`; cố tình giả lập lỗi các kết nối đứng trước để bảo đảm chạy vào thư viện, còn dữ liệu vnstock và giá nguồn khác được tải thật. Đây là kiểm chứng giá, không phải một lượt nghiệm thu toàn báo cáo.

Bản này bổ sung vnstock cho giá chính và nguồn đối chiếu giá chính. Các bảng tài chính KBS, hồ sơ/tin, phân ngành, adapter PDF SHS/HPG và luồng giá của mẫu định giá ngành giữ cơ chế hiện có. Không coi việc thêm thư viện là đã giải quyết thiếu BCTC F88, metadata kỳ 24 tháng hoặc mọi trường hợp thiếu dữ liệu trên HNX/UPCoM.

Tham khảo nguồn chính thức: [vnstock](https://github.com/thinh-vu/vnstock), [component KBS](https://github.com/thinh-vu/vnstock/blob/main/vnstock/explorer/kbs/quote.py), [component VCI](https://github.com/thinh-vu/vnstock/blob/main/vnstock/explorer/vci/quote.py), [chuyển đơn vị](https://github.com/thinh-vu/vnstock/blob/main/vnstock/core/utils/transform.py), [bản 4.0.8](https://pypi.org/project/vnstock/4.0.8/).

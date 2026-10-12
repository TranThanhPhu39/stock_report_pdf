# Bổ sung MBB và định giá ngân hàng

Ngày kiểm chứng: 12/10/2026. Lượt chạy nguồn thật `MBB_20261012_133521_709871`.

## Vấn đề và cách xử lý

KBS gắn nhãn BCTC MBB 2025 nhưng metadata `PeriodBegin=202501`, `PeriodEnd=202612` mô tả 24 tháng và kết thúc sau ngày công bố. Bộ đọc năm loại kỳ này, dùng 2024; khuyến nghị bị chặn do tài chính cũ. Code vẫn giữ kiểm tra đó, bổ sung bộ đọc tài liệu ngân hàng gốc để xác nhận kỳ, phạm vi và đơn vị từ chính PDF.

`src/data/bank_issuer.py` tự tải tài liệu theo cấu hình `config/bank_issuer_sources.json`. PDF phải khớp SHA-256, tên ngân hàng, kiểm toán/soát xét, hợp nhất, triệu VND, thứ tự cột hiện tại/kỳ trước; bảng cân đối và phân bổ LNST phải khớp. Chín chỉ tiêu năm được đối chiếu số với KBS: tài sản, nợ, vốn, vốn NCI, thu nhập lãi thuần, LNST, LNST cổ đông mẹ, LNTT, CFO. Không sửa metadata hoặc tráo năm của KBS.

PDF có text dùng PyMuPDF; bản scan dùng Tesseract `vie+eng`. Một số vùng số scan đã được kiểm tra trực quan và khóa tọa độ với checksum PDF; OCR tại ba độ phân giải phải có ít nhất hai kết quả số đồng thuận. Lưu nguyên dòng, trang, vùng và các lần OCR để kiểm tra lại. OCR không tự thay ký tự thành số hoặc suy ra số cân đối còn thiếu. Dòng bổ sung chưa đối chiếu không được đưa vào chỉ tiêu chính.

## Tài liệu gốc và nơi tải

| Mã/kỳ | Tài liệu | Nơi tải | Trang PDF dùng cho ba bảng |
|---|---|---|---|
| MBB 2025 | BCTC kiểm toán trong BCTN ngân hàng | [Kho công bố FiinGroup](https://cmsv5.fiingroup.vn/medialib/FG/2026/2026-03/2026-03-31/MBB/20260330--MBB--Bao-cao-thuong-nien-2025.pdf) | 144–148, tách trái/phải vì trang đôi |
| MBB bán niên 2026 | BCTC hợp nhất soát xét sáu tháng | [Kho công bố 24HMoney](https://cdn.24hmoney.vn/upload/file/2026-3/2026-08-08/no-name-1786128041.pdf) | 10–15 |
| CTG 2025 | BCTC hợp nhất kiểm toán | [Website VietinBank](https://investor.vietinbank.vn/documents/20126/667477/BCTC%20hop%20nhat%20kiem%20toan%20nam%202025_VN.pdf.pdf/4c8eda02-b420-612d-24ac-c12f2bbd3451) | 8–13 |
| TCB 2025 | BCTC hợp nhất kiểm toán VAS | [Website Techcombank](https://techcombank.com/content/dam/techcombank/public-site/documents/techcombank-vas-consolidated-financial-statements-ye25-searchable.pdf) | 8–12 |

MBB dùng tài liệu do ngân hàng lập được lưu ở kho công bố; không gọi các host này là website MBB. Danh mục API MBB trả 403 cho một số truy vấn, chưa xác minh ngày công bố trên danh mục. Cả bốn cấu hình chỉ nhận tài liệu từ **12/10/2026**, ngày đã trực tiếp xác minh khả dụng công khai. `available_at` là giới hạn bảo thủ, `published_at` để trống; không biến ngày ký/ngày trên tên file thành ngày công bố. Truy vấn lịch sử trước ngày đó giữ nguồn và các giới hạn trước đây. Bản tài liệu mới thay checksum cần được kiểm tra lại trước khi nhận vào cấu hình.

## Kết quả thực tế

- MBB: BCTC hợp nhất 2025/2024 từ PDF và 2023/2022 từ KBS; chín đối chiếu năm 2025 đều khớp. Bốn số dư đầu năm bán niên khớp BCTC 2025; tài sản = nợ + vốn và LNST = cổ đông mẹ + NCI ở cả hai cột.
- Bán niên 2026: thu nhập lãi thuần **31.806,771 tỷ VND**, LNST cổ đông mẹ **15.744,575 tỷ VND**, CFO **−53.201,811 tỷ VND**. Số dư tài sản **1.733.012,662 tỷ VND**, vốn hợp nhất **156.762,644 tỷ VND**. CFO ngân hàng phản ánh tài sản/nợ hoạt động; không áp quy tắc CFO/LNST của doanh nghiệp sản xuất.
- So sánh tài chính CTG, TCB, ACB, VIB cùng năm/phạm vi 2025; CTG/TCB mỗi mã qua chín kiểm tra PDF/KBS. ACB/VIB là dữ liệu nhà cung cấp đã qua kiểm tra kỳ, chưa được chứng nhận độc lập toàn bộ.
- P/B đủ **2 mã CTG/TCB**, trung vị **1,31605 lần**. ACB/VIB thiếu NCI đủ điều kiện để tách vốn mẹ; không tự coi NCI bằng 0. Giá tham chiếu P/B MBB **19.341 VND/CP**.
- P/E đủ **4 mã**, trung vị **7,05339 lần**; mức đối chiếu **20.390 VND/CP**. Với ngân hàng, P/B là phương pháp chính; P/E dùng đối chiếu, không lấy trung bình tùy ý.
- Giá **19.050 VND** ngày **09/10/2026**, mẫu lịch sử khớp **20/20 phiên**. Khuyến nghị **THEO DÕI**, không còn blocker tài chính cũ. P/B chênh **+1,53%**, chưa đạt ngưỡng nghiên cứu tích lũy 15% của đề tài.

Bán niên hiển thị thành hai bảng: luồng lũy kế sáu tháng/cùng kỳ và số dư cuối kỳ/đầu năm. Luận điểm đầu tư cập nhật tăng trưởng thu nhập lãi và lợi nhuận cổ đông mẹ. Gói Gemini có sáu dòng bằng chứng bán niên kèm nguồn và kỳ, phân biệt luồng với số dư; lần kiểm chứng không gọi API Gemini thật.

## Chạy và kiểm chứng

```powershell
.venv\Scripts\python.exe -m scripts.analyze MBB --start 2022-10-13 --as-of 2026-10-12 --output output/pdf/MBB_report.pdf
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Web đang chạy tại `http://localhost:8501`. Chọn MBB, ngày chốt từ 12/10/2026 và bấm **Phân tích và tạo PDF** lại để thay kết quả cũ trong phiên.

Minh chứng lưu tại `submission/evidence/mbb_upgrade/acceptance.json`, `ui_check.json` và các trang PDF render. PDF 20 trang tại `output/pdf/MBB_report.pdf`; các trang tổng quan, tài chính/bán niên, định giá và phương pháp đã kiểm tra trực quan. AppTest dùng kết quả nguồn thật đã lưu, giả lập hai lời gọi phân tích/xuất PDF: không ngoại lệ, có bảng bán niên, trạng thái THEO DÕI, bảy nút tải; đổi bộ lọc biểu đồ không gọi lại pipeline.

Toàn bộ **189 kiểm thử offline đạt**, gồm 18 kiểm thử mới cho PDF ngân hàng, metadata/đơn vị, đối chiếu, lỗi nguồn, kỳ so sánh, bằng chứng AI và điều kiện khuyến nghị. Không đổi ngưỡng khuyến nghị để ép MBB thành mua.

Giới hạn: mẫu nhỏ không đại diện toàn ngành; EPS là lợi nhuận năm chia số CP snapshot hiện tại, không phải TTM/dự phóng. Bán niên không nhân đôi thành năm và chưa dùng P/B bán niên vì thiếu mẫu đồng kỳ. NIM, NPL, CAR chưa được xác minh. Chưa triển khai/kiểm chứng Streamlit Cloud; cấu hình OCR hệ thống đã có trong `packages.txt`.

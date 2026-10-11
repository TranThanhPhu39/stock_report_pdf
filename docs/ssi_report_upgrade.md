# Sửa báo cáo SSI - 11/10/2026

BCTC 2024 cũ do KBS gắn `PeriodBegin=202501`, `PeriodEnd=202612` cho năm 2025, thành 24 tháng. Chọn giá từ 11/10/2025 đến 11/10/2026 không tự chuyển kỳ BCTC: hệ thống dùng BCTC năm hợp lệ được công bố trước ngày chốt. Không đổi nhãn năm nguồn lỗi để làm báo cáo trông mới hơn.

## Dữ liệu và định giá đã kiểm chứng

SSI lấy PDF hợp nhất kiểm toán 2025 từ [danh mục doanh nghiệp](https://www.ssi.com.vn/quan-he-nha-dau-tu/bao-cao-tai-chinh) và [công bố ngày 27/03/2026](https://www.ssi.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/chi-tiet/cong-bo-bctc-rieng-bctc-hop-nhat-va-bao-cao-ty-le-attc-nam-2025-da-kiem-toan). Bộ đọc kiểm tra SSI/kiểm toán, phạm vi hợp nhất, VND, ngày/kỳ, hai cột, từng hàng, tài sản = nợ + vốn, LNTT = đã thực hiện + chưa thực hiện. OCR phải khớp các giá trị KBS cùng cột năm (tối thiểu sáu chỉ tiêu cốt lõi). Năm 2024 trong PDF SSI có trình bày lại: giữ cột so sánh của PDF, không ghép lợi nhuận cũ KBS vào cùng kỳ. SSI chưa tích hợp quý/bán niên 2026; không gọi BCTC 2025 là BCTC mới nhất mà doanh nghiệp từng công bố, hoặc lợi nhuận TTM.

TVS sử dụng [PDF kiểm toán hợp nhất 2025 và công bố chính thức](https://www.tvs.vn/vi/quan-he-nha-dau-tu/bao-cao-tai-chinh-kiem-toan-hop-nhat-nam-2025); kiểm tra tương tự và khớp 12 chỉ tiêu. OCR độ phân giải thấp đọc sai chữ số lợi nhuận chưa thực hiện: đẳng thức lợi nhuận đã chặn lỗi; bản đọc độ phân giải cao khớp đẳng thức và số đối chiếu. Không sửa số OCR bằng số hard-code. PDF/cache có SHA-256; dữ liệu số trích lại từ tài liệu/cache mỗi lượt.

Run thực `SSI_20261011_222135_393293`:

- SSI: 2025/2024 từ PDF, 2023/2022 từ các kỳ KBS hợp lệ; 12 chỉ tiêu 2025 đối chiếu khớp.
- Ngành ICB 8777, 43 thành viên; mẫu đủ dữ liệu cùng kỳ 31/12/2025 gồm VDS và TVS. VDS từ KBS hợp lệ; TVS từ PDF đã đối chiếu. Không chứng nhận toàn bộ số liệu ngành hoặc độc lập nguồn gốc KBS.
- Giá đóng cửa SSI 19.000 VND ngày 09/10/2026; mẫu lịch sử 20/20 khớp.
- SSI P/B 1,79x, P/E năm quy đổi 13,89x; trung vị mẫu tương ứng 0,96x và 10,09x. P/B tham chiếu 10.266 VND; P/E tham chiếu 13.799 VND. Năm/CP snapshot, không phải dự phóng/TTM hoặc giá hợp lý được chuyên gia chứng nhận.
- Quy tắc nghiên cứu trả **ƯU TIÊN QUẢN TRỊ RỦI RO** do chênh lệch P/B tham chiếu -45,97%; không còn bị chặn bởi thiếu kỳ 2025/mẫu cùng năm. Hai doanh nghiệp có quy mô và mô hình khác SSI; giá tham chiếu cần đọc cùng ROE, tăng trưởng và sự khác biệt này. Không tự gán premium để làm giá mục tiêu tăng.
- 13 chỉ tiêu so sánh phù hợp chứng khoán; bổ sung nợ phải trả/vốn, tài sản/vốn, LNST/doanh thu hoạt động, các khoản cho vay/vốn. Các khoản cho vay BCTC không mặc nhiên là dư nợ margin; không áp biên gộp/CFO-LNST/EV-EBITDA doanh nghiệp sản xuất cho chứng khoán.

## Giao diện và PDF

Bỏ câu thông báo dài về Close đã khớp trong Tổng quan; giữ cảnh báo nếu chưa khớp. Biểu đồ web có OHLC, khối lượng, MA và bộ lọc 3/6 tháng/toàn kỳ. Mỗi phần Vĩ mô/Ngành chỉ một ô cập nhật báo chí; dữ liệu lấy tối đa tám bài mỗi phạm vi trong 30 ngày, mặc định ba bài và nút mở/thu gọn. Ba là số thẻ xem trước, không phải tổng tin đã thu thập; tám cũng không phải toàn bộ báo chí. Các kênh vĩ mô vào ngành gộp cùng một ô, giữ nguồn/kỳ và điều kiện theo dõi. Lý do loại peer phân biệt lỗi metadata, thiếu kỳ, khác phạm vi/loại hình, thiếu chỉ tiêu và lỗi nguồn.

PDF bỏ biểu đồ giá lặp ở Tổng quan, dùng tên nguồn thay mã S1/S2, chỉnh nhãn/đơn vị/cỡ chữ và biểu đồ P/E/P/B trực tiếp. Giữ URL và hồ sơ truy vết. Bố cục trái biểu đồ, phải chữ trong phân tích; phụ lục toàn chiều rộng. Các giá trị đối chiếu dùng nhãn tiếng Việt.

## Gemini và giới hạn kiểm chứng

Lỗi cũ chỉ lưu `ValueError`, không lưu thông báo kiểm tra gốc, nên chưa thể kết luận nguyên nhân chính xác của response SSI cũ. Các nguyên nhân có thể bị kiểm tra chặn gồm số/ngày chưa đối chiếu, mã dẫn nguồn không khớp, thiếu liên kết bằng chứng hoặc JSON sai. Bản mới gắn nguồn từ evidence IDs, cho phép MA20/MA50, giữ riêng từng nhận xét hợp lệ và hiển thị lý do loại bằng tiếng Việt. Không xuất SDK error text có thể chứa khóa/URL nhạy cảm.

Gemini hỗ trợ diễn giải vĩ mô/ngành và kết nối tới doanh thu, chi phí, rủi ro của doanh nghiệp; nhận xét xuất hiện ở các mục tương ứng và PDF nếu bật AI và qua kiểm tra. Chương trình tính tài chính/định giá/khuyến nghị. Kiểm tra dẫn nguồn/định dạng không chứng nhận mọi suy luận đúng. Run kiểm chứng này tắt AI để không đưa phản hồi giả vào báo cáo.

Automatic approval review đã từ chối gửi gói bằng chứng SSI tới Google/Gemini vì chưa có chấp thuận cụ thể cho payload/destination. Không đọc key hoặc gọi API trong bước bị từ chối. Cần người dùng cho phép gửi gói dữ liệu này để kiểm chứng API thật; kiểm thử SDK HTTP giả lập không thay thế kiểm chứng API/Cloud.

OCR trên Community Cloud cần các dependency hệ thống trong `packages.txt`, theo [Streamlit Docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies). Chưa triển khai hoặc xác nhận Cloud trong phiên này.

## Minh chứng

`submission/evidence/ssi_report_upgrade.json` và `ssi_ui_upgrade.json`. Bộ kiểm thử offline, AppTest với kết quả nguồn thực, PDF render toàn bộ và kiểm tra nhãn/phân trang. Đây là kiểm chứng SSI và adapter TVS, không phải toàn thị trường.

Kiểm chứng cuối: 170 kiểm thử offline đạt; AppTest SSI và hồi quy SHS/VNM/REE không ngoại lệ; PDF SSI 17 trang đã render và kiểm tra toàn bộ.

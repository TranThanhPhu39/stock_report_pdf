# TTM và NIM/NPL/CAR MBB

Đợt bổ sung ngày 12/10/2026 tiếp nối [bộ đọc BCTC ngân hàng](mbb_bank_upgrade.md). Tự tải nguồn khi phân tích; không yêu cầu người dùng nhập các tỷ lệ hoặc lợi nhuận TTM.

## Nguồn và kỳ

- [BCTN MBB 2025, tài liệu ngân hàng trong kho công bố FiinGroup](https://cmsv5.fiingroup.vn/medialib/FG/2026/2026-03/2026-03-31/MBB/20260330--MBB--Bao-cao-thuong-nien-2025.pdf): trang PDF 46 trái (bảng chỉ tiêu), 58 phải (NIM có nguồn BCTC hợp nhất), 67 phải (CAR hợp nhất), 161 trái (thuyết minh 9.1 chất lượng cho vay). Trang PDF khác số trang in vì mỗi trang PDF gồm hai trang sách.
- [BCTC hợp nhất soát xét MBB bán niên 2026, kho công bố 24HMoney](https://cdn.24hmoney.vn/upload/file/2026-3/2026-08-08/no-name-1786128041.pdf): trang 13 cho lợi nhuận hiện tại và cột cùng kỳ.
- [BCTC TCB 2025, website ngân hàng](https://techcombank.com/content/dam/techcombank/public-site/documents/techcombank-vas-consolidated-financial-statements-ye25-searchable.pdf): trang 11 trình bày NCI trong ngoặc như khoản khấu trừ từ lợi nhuận hợp nhất để ra lợi nhuận mẹ. Cấu hình khóa quy ước `deduction_to_parent` theo checksum này; không áp `abs()` cho NCI của mọi ngân hàng.

Không suy diễn ngày công bố từ ngày ký hoặc tên file. Tài liệu cấu hình mới vẫn chỉ khả dụng từ ngày trực tiếp xác minh 12/10/2026; ngày công bố để trống. Bản PDF thay checksum phải được kiểm tra lại.

## Công thức và kết quả

| Chỉ tiêu | Kỳ | Kết quả | Cách xác định |
|---|---|---|---|
| NIM hợp nhất | 2025 | 3,9%; 2024: 4,2% | Số ngân hàng công bố, xác nhận phạm vi ở trang 58. Chưa tái tính từ tài sản sinh lãi bình quân. |
| CAR hợp nhất | Cuối 2025 | 11,0%; 2024: 11,8% | Số ngân hàng công bố, đối chiếu nhận xét CAR hợp nhất trang 67. Chưa tái tính vốn tự có/RWA. |
| NPL tính lại | Cuối 2025 | 1,294026%; 2024: 1,620460% | Nợ nhóm 3–5 / tổng cho vay gộp hợp nhất thuyết minh 9.1 × 100. |
| LNST cổ đông mẹ TTM | 01/07/2025–30/06/2026 | 30.078,169 tỷ VND | 26.778,939 + 15.744,575 − 12.445,345. |
| LNST hợp nhất TTM | 01/07/2025–30/06/2026 | 30.851,586 tỷ VND | 27.382,978 + 16.148,193 − 12.679,585. |

NPL: nợ nhóm 3–5 là 14.027,496 tỷ VND; mẫu số là 1.084.019,370 tỷ VND. Tổng các nhóm nợ và khoản margin/ứng trước chứng khoán phải khớp tổng cho vay ở cả hai cột. Kết quả khớp mức ngân hàng công bố 1,3% trong sai số làm tròn một chữ số; không xác nhận mọi quy ước phân loại của tỷ lệ công bố. Không dùng tổng tín dụng gồm trái phiếu làm mẫu số thay thế.

TTM = năm trước + lũy kế hiện tại − lũy kế cùng kỳ năm trước. Hiện triển khai cho bán niên đúng 01/01–30/06 cùng phạm vi hợp nhất và VND; không tự cộng quý lũy kế, không nhân đôi bán niên thành dự báo. Cột cùng kỳ dùng bản bán niên mới nhất đã xác minh. Ba đầu vào lợi nhuận phải có kỳ và nguồn, khả dụng trước ngày chốt, và phân bổ hợp nhất = mẹ + NCI phải khớp. Giữ nguồn/trang/giá trị của từng toán hạng.

P/E TTM = giá đóng cửa đã đối chiếu × số CP snapshot / LNST cổ đông mẹ TTM. Đây là bội số vốn hóa tham khảo; lợi nhuận chia CP snapshot khác EPS bình quân gia quyền ngân hàng công bố. Chưa có mẫu TTM đồng kỳ, nên không so P/E TTM MBB với trung vị P/E năm 2025, không đưa bội số nhập tay vào khuyến nghị chính.

UI/PDF tách bảng tỷ lệ ngân hàng, bảng cầu nối TTM và bội số P/E TTM khỏi định giá mẫu năm. Chỉ tiêu có kỳ riêng và cách xác định; cảnh báo thiếu NIM/NPL/CAR phát sinh theo dữ liệu thực tế. Các bằng chứng tỷ lệ và TTM được đưa vào bundle Gemini tùy chọn; đợt kiểm chứng này không gọi Gemini thật.

## Phạm vi

Bộ đọc tỷ lệ gốc mới xác minh **MBB**, không tuyên bố đã đủ cho mọi ngân hàng. NIM/NPL/CAR hiện là kỳ **2025**, không phải bán niên 2026 hoặc thời gian thực. Chưa có mẫu P/E TTM/P/B bán niên đồng kỳ; chưa tái tính NIM/CAR từ toàn bộ thuyết minh. Chưa kiểm chứng Streamlit Cloud.

Minh chứng của đợt này: `submission/evidence/mbb_metrics_upgrade/acceptance.json`, các trang PDF render và `output/pdf/MBB_report.pdf`. Minh chứng đợt trước trong `mbb_upgrade/` giữ nguyên như lịch sử; PDF hiện tại là bản đã bổ sung.

Kiểm chứng: **202 kiểm thử offline đạt**, trong đó 13 kiểm thử mới cho tỷ lệ, thứ tự cột, sai đơn vị/phạm vi/kỳ, thiếu dữ liệu, tổng nhóm nợ, phân bổ NCI và chặn P/E TTM khi giá chưa xác minh. AppTest dùng kết quả nguồn thật đã lưu: bảng tỷ lệ/TTM/P/E TTM hiển thị, không ngoại lệ, bảy nút tải; đổi khoảng biểu đồ không gọi lại pipeline. PDF đầy đủ **20 trang** và bản tóm tắt có cả ba mục mới; trang tỷ lệ, TTM, định giá và phương pháp đã render, kiểm tra trực quan cùng contact sheet toàn báo cáo.

Trong lượt kiểm chứng giá 19.050 VND ngày 09/10/2026, số CP snapshot 12/10/2026 là 9.263.249.895: **P/E TTM 5,86688 lần**. Mẫu năm giữ CTG/TCB/ACB/VIB, P/E bốn mã và P/B hai mã; P/B chính 19.341 VND, chênh +1,53%. Khuyến nghị vẫn **THEO DÕI**, không nới ngưỡng để tạo nhãn mua. Hai phép đối chiếu tỷ lệ là đối chiếu nội bộ cùng tài liệu gốc, không gọi là hai nguồn độc lập.

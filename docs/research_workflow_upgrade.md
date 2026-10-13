# Dữ liệu quý/TTM, tóm tắt quyết định và so sánh mã tự chọn

Đợt triển khai 13/10/2026 giữ phạm vi web tạo báo cáo cổ phiếu. Không thêm danh mục, giá vốn, phân bổ vốn hoặc theo dõi giao dịch cá nhân.

## Cách sử dụng

1. Nhập mã chính và ngày phân tích như trước.
2. Nếu cần, mở **So sánh với các mã bạn chọn**, nhập tối đa bốn mã khác, cách nhau bằng dấu phẩy hoặc khoảng trắng. Mã trùng được loại bỏ; tổng tối đa năm mã tính cả mã chính.
3. Chọn **Phân tích ngành** để đưa bảng so sánh vào PDF. Giao diện vẫn trình bày kết quả so sánh ở tab **Ngành**.
4. Bấm **Phân tích và tạo PDF**. Mỗi mã bổ sung được lấy dữ liệu mới; thời gian chờ tăng theo số mã và tốc độ nguồn.
5. Đọc phần tóm tắt quyết định ở đầu kết quả, dữ liệu quý/TTM ở tab **Tài chính**, và bảng mã tự chọn ở tab **Ngành**. Có nút tải CSV cho bảng so sánh.

Ví dụ dòng lệnh:

```powershell
py -3.12 -m scripts.analyze SSI --start 2026-01-01 --as-of 2026-10-13 --compare MBB --mode summary --sections overview industry financial valuation risks
```

## Dữ liệu quý và TTM

- Bộ đọc mới lấy kết quả kinh doanh quý trực tiếp từ Vietcap, lưu JSON gốc theo lượt chạy và lọc cả ngày công bố lẫn ngày sửa đổi. Có thể đọc nhiều ngành; doanh thu dùng cho phi tài chính/chứng khoán, thu nhập lãi thuần dùng cho ngân hàng.
- Kiểm tra mã, năm, quý, ngày, số hữu hạn và các bản trùng mâu thuẫn. Không suy đoán ngày công bố thiếu. KBS quý không được dùng do kiểm tra nguồn thật phát hiện metadata/cột trùng hoặc sai ánh xạ.
- **Quan sát TTM từ nhà cung cấp** chỉ cộng bốn quý riêng liên tiếp. Kiểm tra thang VND bằng đối chiếu lợi nhuận năm với đầu vào tài chính chính. Vietcap chưa khai báo phạm vi từng quý; quan sát này không thay TTM đã xác minh, P/E định giá hoặc khuyến nghị.
- **TTM đã xác minh** lấy năm trước + bán niên hiện tại - bán niên cùng kỳ, cùng phạm vi hợp nhất và đơn vị VND. Mỗi chỉ tiêu giữ ba đầu vào, nguồn và ngày công bố. Thiếu LNST mẹ thì không lấy LNST hợp nhất thay thế.
- SSI bổ sung bộ đọc PDF hợp nhất soát xét bán niên chính thức. Kiểm tra ngày công bố trong PDF, sáu tháng đúng năm, đơn vị, số dư hai cột và cân đối tài sản. Số dư đầu năm phải khớp báo cáo năm; doanh thu/LNST/LNST mẹ hiện tại phải khớp Q1+Q2 Vietcap. Giữ cột cùng kỳ đã trình bày lại trong PDF, bao gồm quy ước phân bổ quỹ.
- Ngân hàng giữ bộ ghép TTM nghiêm ngặt hiện có; không dùng bộ ghép tổng quát để bỏ qua kiểm tra phân bổ lợi nhuận ngân hàng. Bộ ghép tổng quát mới hỗ trợ các bán niên hợp lệ của doanh nghiệp phi ngân hàng, bao gồm SSI và HPG khi đầu vào đạt.
- CFO quý chưa được cộng vì chưa xác nhận cơ sở riêng quý/lũy kế của nguồn. CFO TTM chỉ được ghép khi có đầu vào năm/bán niên hợp lệ.
- P/E TTM là tham khảo riêng. Định giá chính vẫn sử dụng mẫu P/E/P/B năm đồng kỳ; không lấy mẫu P/E năm nhân lợi nhuận TTM để tạo giá mục tiêu.

## Tóm tắt quyết định

Giao diện và PDF dùng chung hàm tóm tắt. Ngay cạnh kết luận có phương pháp, kỳ/phạm vi tài chính, số peer của phương pháp chính nếu áp dụng, độ tin cậy, khoảng min-max các phương pháp, độ phân tán, các điều kiện còn thiếu và rủi ro chính. Khoảng giá không được gọi là khoảng xác suất. Dữ liệu quý và TTM mới hơn được ghi riêng.

Khuyến nghị không còn đề xuất tích lũy chỉ dựa trên tăng trưởng năm cũ nếu LNST mẹ của bán niên mới đã xác minh đang giảm so với cùng kỳ.

## So sánh nhiều mã

- Mã chính là điểm neo; so sánh cùng ngày chốt.
- Tìm ngày cuối kỳ năm/phạm vi chung gần nhất trong các kết quả có tài chính hợp lệ. Nếu dùng kỳ cũ hơn, ghi rõ. Nếu không có kỳ/phạm vi chung, ẩn chỉ tiêu tài chính và bội số khác cơ sở.
- P/E năm dùng lợi nhuận mẹ năm, P/B dùng vốn mẹ; cả hai yêu cầu giá đã đối chiếu đúng ngày và CP snapshot đúng ngày chốt. P/E TTM chỉ hiển thị khi các mã có TTM đã xác minh cùng khoảng 12 tháng/phạm vi với mã chính.
- CFO/LNST và nợ vay/vốn chỉ áp dụng phi tài chính. Không đồng nhất doanh thu của doanh nghiệp thường với thu nhập lãi ngân hàng.
- Bảng mã người dùng chọn không thay mẫu định giá ngành và không tự xếp hạng mua/bán.
- Khi một mã lỗi, báo lỗi riêng và giữ kết quả mã chính/các mã còn lại.

## Kiểm chứng thực tế

Lượt chạy `SSI_20261013_134650_710317` đã hoàn tất với trạng thái pipeline `analyzed`, dùng giá ngày 12/10/2026 và CP snapshot ngày 13/10/2026:

| Chỉ tiêu | SSI | MBB |
| --- | ---: | ---: |
| BCTC năm so sánh | 2025-12-31 hợp nhất | 2025-12-31 hợp nhất |
| Ngày kết thúc TTM đã xác minh | 2026-06-30 | 2026-06-30 |
| P/E năm | 13,92 | 6,62 |
| P/E TTM tham khảo | 11,65 | 5,90 |
| P/B | 1,79 | 1,30 |

SSI đọc được 34 kỳ quý. LNST mẹ TTM theo công thức năm + bán niên - cùng kỳ: **4.908.807.960.282 VND**. Đây là minh chứng cho lượt chạy tại ngày nêu trên, không phải báo giá hiện tại hoặc khuyến nghị giao dịch. `analyzed` là trạng thái thực thi phân tích, không đảm bảo có giá mục tiêu chính đủ dữ liệu.

Kiểm tra cuối đã hoàn tất:

- **232 kiểm thử** đạt, gồm hồi quy cho cấu trúc danh mục SSI thật và điều kiện bán niên mới/cũ.
- **Streamlit AppTest** chạy không có exception với kết quả SSI–MBB đã lưu; xác nhận tám tab và nút tải CSV so sánh. Kiểm tra này dùng kết quả đã lưu, không gọi lại nguồn mạng.
- PDF mẫu `output/pdf/SSI_research_upgrade.pdf` được xuất lại, render và kiểm tra trực quan đủ **14 trang**. Đã sửa tiêu đề TTM bị tách khỏi bảng sang trang khác; không thấy chữ/bảng chồng lên nhau hoặc bị cắt trong bản mẫu.
- Sau chỉnh bố cục, **20 kiểm thử tài chính/báo cáo** chạy lại đều đạt; AppTest và render PDF cũng được chạy lại thành công. Script kiểm tra nằm ở `tmp/verify_research_upgrade.py`.

Lượt SSI mẫu vẫn ghi **chưa đủ cơ sở khuyến nghị** do thiếu phương pháp định giá chính đủ điều kiện; có TTM và bảng so sánh không tự tạo ra giá mục tiêu.

## Mã nguồn chính

- `src/data/quarterly.py`: dữ liệu quý và quan sát TTM.
- `src/data/ssi_interim.py`: PDF bán niên SSI và đối chiếu.
- `src/analysis/trailing.py`: ghép TTM phi ngân hàng từ đầu vào đã kiểm tra.
- `src/analysis/decision.py`: tóm tắt chung UI/PDF.
- `src/analysis/comparison.py`: so sánh đồng kỳ và các điều kiện bội số.
- `tests/test_quarterly_comparison.py`: hồi quy về dữ liệu quý, TTM, SSI và so sánh mã.

Nguồn gốc: [Vietcap IQ](https://iq.vietcap.com.vn/), [danh mục BCTC SSI](https://www.ssi.com.vn/quan-he-nha-dau-tu/bao-cao-tai-chinh). Adapter HTTP được kiểm tra theo [mã nguồn provider VCI của vnstock](https://github.com/thinh-vu/vnstock/blob/main/vnstock/explorer/vci/financial.py); không cần cài vnstock để chạy bộ đọc quý mới.

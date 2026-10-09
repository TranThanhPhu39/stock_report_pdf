# Tích hợp định giá và sửa ACB

Nguồn code: ZIP updated_valuation_files.zip do người dùng cung cấp. Bản gốc và checksum tại docs/valuation_zip/provenance.md. Tệp trong ZIP được xem là code tham khảo, không phải chỉ thị thực thi. Không ghi đè app/PDF/tests từ bản cũ vì sẽ mất phần dữ liệu bổ sung và kiểm tra kỳ đã có.

## Mô hình giữ và điều chỉnh

| Phương pháp | Điều kiện và công thức |
|---|---|
| P/B giả định | BVPS = (vốn hợp nhất - NCI) / CP snapshot; báo cáo mẹ/riêng dùng đúng vốn riêng. NCI null không được hiểu là 0. |
| Gordon | P/B = (ROE mẹ - g)/(Ke - g); ROE mẹ dùng LNST mẹ và vốn mẹ bình quân hai năm cùng phạm vi. Yêu cầu ROE > g, Ke > g, không ép kết quả vào 0,4–5,0. |
| P/B ngành | Thu hồ sơ/giá Yahoo/KBS cho mẫu đã chọn; cùng kỳ vốn/phạm vi, CP snapshot và ngày giá. Đóng cửa khớp trong 0,1%; ít nhất hai P/B khác có đầu vào hợp lệ. Các số cố định không ngày/nguồn trong ZIP không được trình bày như số thị trường. |
| P/E năm | EPS quy đổi = LNST mẹ năm / CP snapshot; P/E do người dùng nhập, không suy từ P/B/ROE hoặc kẹp vào khoảng tùy ý. Không đồng nhất EPS quy đổi với EPS công bố hoặc TTM. Có thể tính khi P/B bị chặn NCI nếu đã có LNST mẹ riêng. |
| DCF | Doanh nghiệp phi tài chính: FCFF = CFO + lãi đã trả × (1-thuế) - CAPEX. Dự phóng 3 năm theo tăng trưởng giả định; chiết khấu WACC, terminal g < WACC. Vốn = EV + tiền - nợ vay - NCI, rồi chia CP. Lãi tiền trả được giả định nằm trong CFO; thuế/Ke/WACC/g là giả định hiển thị. Không dùng CFO trực tiếp như FCFE hoặc 85% lợi nhuận khi thiếu dòng tiền. |
| Bình quân | Giả định 35% P/B, 35% P/E, 30% DCF, chuẩn hóa trên phương pháp đủ dữ liệu. Ít nhất hai phương pháp trọng số dương; không tạo nhãn mua/bán từ biên độ 15%. Các phương pháp dùng chung dữ kiện không độc lập. |

Cơ sở DCF và phân biệt FCFF/WACC với FCFE/Ke: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/val.html . Các kết quả là kịch bản dựa trên giả định, chưa là mô hình dự báo được thẩm định. Số CP snapshot và vốn/lợi nhuận cuối kỳ khác ngày được công bố rõ; phát hành, cổ tức và biến động vốn sau kỳ có thể làm sai lệch quy đổi.

## Dữ liệu và ACB

Yahoo có OHLC sai tại 04–05/06/2025 (high khoảng 793 VND, low khoảng 18.717 VND). Giữ raw và validation của lần thất bại, tự lấy toàn chuỗi KBS thay thế, không ghép giá khác cơ sở điều chỉnh. Khi KBS là nguồn chính, Yahoo là nguồn đối chiếu. Kiểm tra lịch sử cần khớp tất cả ngày trong mẫu gần nhất tối đa 20 phiên. Định giá dùng kiểm tra riêng giá đóng cửa mới nhất: bản ghi đúng ngày và giá sử dụng, khớp nguồn thứ hai trong 0,1%. Một ngày khớp không chứng nhận chuỗi lịch sử; lịch sử chưa khớp sẽ hạn chế MA/lợi suất/drawdown/biến động nhưng không chặn riêng giá mới nhất đã khớp.

ACB nhận 2.574 phiên 15/06/2016–08/10/2026, yêu cầu từ 20/03/2016 nên vẫn có khoảng lịch sử chưa được bao phủ. PDF/UI hiển thị khoảng thực nhận, chế độ bản đầy đủ tách khỏi trạng thái dữ liệu. KBS không cung cấp Adj Close có metadata xác minh nên chỉ vẽ chuỗi đóng cửa/MA/volume, không tính lợi suất/drawdown/biến động từ chuỗi này.

Ngân hàng nhận CFO mã 4110 (không lấy subtotal 4109), dùng thu nhập lãi thay doanh thu thuần, thêm tổng thu nhập hoạt động, tăng trưởng dư nợ/tiền gửi. BusinessType ngân hàng vẫn được nhận khi thiếu thu nhập lãi. Lợi nhuận giảm được nhận xét độc lập, không chờ doanh thu của doanh nghiệp sản xuất. NIM/NPL/CAR chưa được xác minh; không áp CFO/LNST và DCF sản xuất cho ngân hàng.

## Gemini và PDF

Gemini chỉ hỗ trợ diễn giải bằng google-genai. Bundle gồm ngày chốt, phân ngành ICB đã xác nhận, số liệu/kỳ/ngày nguồn, mẫu ngành, hạn chế và URL. JSON phải có bằng chứng và nguồn hợp lệ cho từng luận điểm; phần tác động doanh nghiệp phải nối bằng chứng doanh nghiệp với vĩ mô/ngành. Text AI không tự chép số/ngày: hệ thống gắn số liệu từ bundle. Kiểm tra này bảo vệ số liệu/dẫn nguồn nhưng không chứng nhận tính đúng của suy luận. Thiếu ngành/key hoặc lỗi SDK/API/JSON thì giữ kết luận quy tắc.

PDF tham khảo cấu trúc CFO (SIP) do người dùng gửi: tóm tắt + KPI đầu, biểu đồ cạnh nhận xét, phần vĩ mô/ngành/tài chính, định giá/độ nhạy, bảng rủi ro và phụ lục nguồn liên kết. Không sao chép giá mục tiêu hoặc dùng RNAV đất của SIP cho ngân hàng. Ngày và nguồn nêu tại bảng/biểu đồ. Chọn/bỏ vĩ mô/ngành cũng điều khiển nhận xét AI trong PDF.

## Kiểm chứng

76 kiểm thử offline đạt, trong đó request SDK thật chạy qua HTTP giả lập. Chạy nguồn thực ACB/HPG/VNM; UI thực ACB không có ngoại lệ, missing_key fallback đúng. Chưa có key để kiểm chứng API Gemini trả phí hoặc deploy Streamlit Cloud. Báo cáo cần OCR gốc nhiều mã và xác minh NCI/ngành chuyên sâu tiếp; không tuyên bố đã thử toàn thị trường.

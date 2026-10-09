# Kiến trúc dự kiến

Chưa triển khai. Luồng: yêu cầu -> đọc nguồn -> chuẩn hóa/kiểm tra -> phân tích -> kết quả thống nhất -> giao diện và PDF.

Pipeline chặn chỉ tiêu không đủ điều kiện và lưu trạng thái thiếu/lỗi. UI và PDF dùng cùng AnalysisResult.

`src/models.py` định nghĩa hợp đồng; `src/pipeline.py` điều phối. Mỗi lần chạy lưu request.json, validation.json, analysis.json, figures/ và report.pdf trong `outputs/runs/<TICKER>_<timestamp>/`.

Xem `../projectcontext.md` và `../task.md` để biết phạm vi và nghiệm thu.

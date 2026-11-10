# Quy tắc phát triển dự án Quản lý bãi giữ xe

Các hướng dẫn này áp dụng cho mọi thay đổi mã nguồn trong dự án. Ưu tiên bảo toàn hành vi hiện có, thay đổi nhỏ nhưng đầy đủ, và chỉ thêm cấu trúc khi nhu cầu thực tế yêu cầu.

## 1. Công nghệ và nền tảng

- Dự án là ứng dụng desktop Python chạy trên Windows; giao diện dùng PySide6.
- Dùng đúng các thư viện hiện có trong `requirements.txt`: OpenCV cho hình ảnh, Ultralytics/YOLO và PaddleOCR cho nhận diện, Pandas/Openpyxl cho dữ liệu Excel.
- Không tự ý thay framework, thêm thư viện hoặc đổi định dạng lưu trữ. Nêu rõ lý do và cập nhật `requirements.txt` nếu yêu cầu thực sự cần thay đổi phụ thuộc.
- Tôn trọng giới hạn tương thích của PaddlePaddle trên Windows. Tham khảo hướng dẫn cài đặt hiện tại trong `README.md`; không mặc định phiên bản Python mới nhất luôn được hỗ trợ.

## 2. Kiến trúc và ranh giới module

Giữ trách nhiệm module rõ ràng theo cấu trúc hiện tại:

| Module | Trách nhiệm |
|---|---|
| `main.py` | Khởi tạo ứng dụng, chuẩn bị dữ liệu và mở cửa sổ chính. |
| `ui.py` | Giao diện, điều phối tương tác và hiển thị trạng thái/kết quả/lỗi. |
| `camera_thread.py` | Đọc khung hình từ webcam hoặc video và phát cập nhật cho giao diện. |
| `anpr.py` | Nạp model, phát hiện/cắt biển số, OCR và chuẩn hóa kết quả. |
| `excel_db.py` | Đọc, kiểm tra và ghi dữ liệu nhân viên/nhật ký Excel. |

- Đặt logic theo đúng trách nhiệm; không đưa xử lý Excel hoặc suy luận model trực tiếp vào widget.
- `ui.py` gọi các hàm nghiệp vụ hoặc `ExcelDatabase`; không tự mở/ghi tệp dữ liệu.
- Không để `anpr.py`, `camera_thread.py` hoặc `excel_db.py` phụ thuộc ngược vào giao diện.
- Giữ giao diện dữ liệu hiện có giữa các module ổn định. Nếu đổi cấu trúc dữ liệu hoặc chữ ký được module khác sử dụng, cập nhật đồng bộ tất cả nơi gọi và tài liệu liên quan.
- Không tái cấu trúc toàn bộ dự án chỉ để áp dụng một mô hình kiến trúc mới. Chỉ tách module/lớp khi điều đó làm trách nhiệm rõ ràng hơn hoặc tránh lặp logic thực sự.

## 3. Quy tắc Clean Code

- Viết Python dễ đọc, tuân theo PEP 8 và giữ phong cách đặt tên hiện có: `snake_case` cho hàm/biến, `PascalCase` cho lớp, `UPPER_SNAKE_CASE` cho hằng số.
- Tên mã nguồn nên mô tả đúng mục đích; nội dung giao diện và thông báo cho người dùng viết bằng tiếng Việt nhất quán với ứng dụng.
- Mỗi hàm/lớp có trách nhiệm rõ ràng. Tách hàm khi có thể đặt tên cho một bước xử lý riêng; tránh hàm dài, lồng điều kiện sâu hoặc nhiều cờ điều khiển khó hiểu.
- Tránh lặp quy tắc nghiệp vụ, đặc biệt là chuẩn hóa biển số, kiểm tra dữ liệu nhân viên và truy cập Excel. Tái sử dụng hàm/điểm truy cập hiện có.
- Dùng `pathlib.Path` cho đường dẫn. Không thêm đường dẫn tuyệt đối của máy cá nhân; model YOLO mặc định phải được định vị từ thư mục dự án và tiếp tục hỗ trợ cấu hình `PARKING_PLATE_MODEL`.
- Thêm type hints khi chúng giúp làm rõ giao diện mới hoặc dữ liệu phức tạp; không dùng ép kiểu bỏ qua kiểm tra kiểu để che lỗi.
- Chỉ thêm chú thích/docstring để giải thích lý do hoặc hành vi không hiển nhiên; không chú thích lại điều mà mã đã nói rõ.
- Không để placeholder, nhánh giả thành công, `pass` che lỗi, hoặc `TODO` thay cho phần triển khai được yêu cầu.

## 4. Giao diện, luồng nền và tài nguyên

- Không chạy đọc video, nhận diện model hoặc thao tác chậm trên luồng giao diện. Dùng QThread/worker phù hợp với mẫu hiện có.
- Từ worker, cập nhật giao diện qua Qt signals/slots; không thao tác trực tiếp widget từ luồng nền.
- Bảo đảm worker và camera được dừng/đợi giải phóng khi đóng cửa sổ hoặc thay nguồn. Giải phóng `VideoCapture` kể cả khi có lỗi.
- Không khởi chạy đồng thời nhiều thao tác nhận diện không an toàn trên cùng tài nguyên dùng chung; tuân thủ các khóa đồng bộ hiện có trong `anpr.py` và `excel_db.py`.
- Hiển thị trạng thái đang xử lý, thành công và thất bại rõ ràng; tránh khóa giao diện hoặc để nút thao tác ở trạng thái vô hiệu hóa sau khi worker kết thúc.

## 5. Dữ liệu và xử lý lỗi

- Mọi thao tác với `staff.xlsx` và `parking_logs.xlsx` đi qua `ExcelDatabase`; giữ đúng tên cột và quy tắc dữ liệu hiện hành.
- Kiểm tra dữ liệu đầu vào trước khi ghi. Không lưu hồ sơ nhân viên thiếu trường bắt buộc hoặc trùng mã/biển số theo quy tắc chuẩn hóa.
- Không thay đổi hoặc xóa dữ liệu lịch sử ngoài yêu cầu rõ ràng; thao tác xóa hồ sơ nhân viên không được âm thầm làm mất nhật ký cũ.
- Bắt lỗi cụ thể tại ranh giới có thể xử lý; chuyển lỗi về giao diện bằng thông báo hữu ích. Không nuốt ngoại lệ, không dùng giá trị mặc định tạo cảm giác thao tác đã thành công.
- Khi tệp Excel bị khóa, thiếu cột hoặc không thể đọc/ghi, giữ cách thông báo rõ nguyên nhân và hướng dẫn người dùng phù hợp.
- Không ghi dữ liệu cá nhân, nội dung tệp Excel hoặc thông tin nhạy cảm vào log/commit nếu không cần thiết.

## 6. Model và cấu hình

- Dùng checkpoint YOLO của dự án tại `models\license_plate_yolov8n.pt` theo đường dẫn tương đối với mã nguồn; cho phép `PARKING_PLATE_MODEL` ghi đè như hiện tại.
- Không đưa đường dẫn model, cache hoặc cấu hình đặc thù máy phát triển vào mã nguồn.
- Giữ rõ khác biệt giữa checkpoint YOLO đã huấn luyện cho biển số và weights YOLO COCO gốc; không chấp nhận âm thầm model sai mục đích.
- PaddleOCR có thể cần tải model riêng ở lần đầu. Khi thay đổi cách khởi tạo, phụ thuộc model hoặc yêu cầu kết nối mạng, cập nhật `README.md`.
- Chỉ phân phối checkpoint/model và dữ liệu huấn luyện khi có quyền sử dụng và phân phối.

## 7. Kiểm thử và xác minh thay đổi

- Trước khi sửa, đọc module và cách gọi liên quan; kiểm tra thay đổi có sẵn trong worktree và không ghi đè công việc khác.
- Chạy kiểm tra nhỏ nhất có thể xác minh yêu cầu: test tương ứng nếu có, hoặc kiểm tra import/biên dịch và hành vi bị ảnh hưởng. Không tuyên bố test đã chạy nếu chưa chạy.
- Với thay đổi nhận diện, kiểm tra cả model được tìm thấy/nạp đúng và trường hợp lỗi phù hợp; tránh chỉ kiểm tra giao diện hoặc proxy không liên quan.
- Với thay đổi dữ liệu, xác minh tên cột, quy tắc kiểm tra và kết quả đọc/ghi liên quan.
- Không tạo hoặc sửa dữ liệu Excel thật trong quá trình kiểm thử nếu không cần; dùng dữ liệu tạm hoặc mock khi phù hợp.
- Báo rõ kiểm tra đã chạy, kết quả và các giới hạn chưa xác minh.

## 8. Tài liệu và quản lý thay đổi

- Cập nhật `README.md` khi thay đổi ảnh hưởng đến cài đặt, cấu hình, model, quy trình sử dụng hoặc giới hạn hệ thống.
- Không sao chép toàn bộ README vào tài liệu hướng dẫn AI; quy tắc này chỉ nêu những ràng buộc cần thiết khi sửa mã.
- Giữ thay đổi tập trung vào yêu cầu. Không tự ý xóa, hoàn tác hoặc ghi đè sửa đổi có sẵn của người dùng.
- Trước khi kết thúc, tóm tắt các tệp/hành vi đã thay đổi và kết quả xác minh.

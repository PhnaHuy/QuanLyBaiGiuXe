# Quản lý bãi giữ xe thông minh

Ứng dụng desktop Windows viết bằng Python, giao diện tiếng Việt, dùng PySide6, OpenCV, Pandas, Openpyxl và msoffcrypto-tool. Dữ liệu được lưu trong hai tệp Excel cạnh chương trình: `staff.xlsx` và `parking_logs.xlsx`; ảnh lượt xe được lưu trong thư mục `captures`.

## Cài đặt

1. Cài Python 3.13 bản 64-bit. PaddlePaddle hiện chưa cung cấp gói cài Windows cho Python 3.14.
2. Mở PowerShell tại thư mục `QuanLyBaiGiuXe`, tạo môi trường riêng và cài thư viện:

   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Ở lần nhận diện đầu tiên, PaddleOCR cần tải các model tiếng Anh; hãy bảo đảm máy có kết nối Internet.
4. Khởi chạy:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

Hai tệp Excel mẫu sẽ được tạo tự động khi khởi động lần đầu. `staff.xlsx` được mã hóa bằng mật khẩu Admin (`123`); nếu đã có `staff.xlsx` chưa mã hóa, chương trình sẽ kiểm tra cấu trúc, giữ nguyên nội dung và mã hóa tệp khi khởi động. Hãy đóng workbook trong Microsoft Excel trước khi chạy ứng dụng. Khi mở trực tiếp `staff.xlsx`, nhập mật khẩu Admin để xem dữ liệu.

## Sử dụng

- **Đăng nhập:** chọn vai trò **Admin** hoặc **Nhân viên** trước khi ứng dụng khởi tạo dữ liệu. Admin đăng nhập bằng mật khẩu mặc định `123` và có đầy đủ chức năng; Nhân viên không cần mật khẩu và chỉ thấy **Điều hành** cùng **Đối chiếu lượt xe**. Nhấn **Đăng xuất** trên Dashboard để kết thúc phiên và quay lại chọn vai trò mà không cần khởi động lại ứng dụng. Mật khẩu mặc định được khai báo trong mã nguồn, vì vậy đây là phân quyền giao diện cục bộ, không thay thế xác thực an toàn khi phân phối hoặc dùng dữ liệu nhạy cảm.
- **Điều hành:** nhập chỉ số webcam (ví dụ `0`, `1`) hoặc chọn tệp video, bấm **Mở nguồn**, sau đó bấm nút ghi nhận tương ứng. Nhận diện và ghi Excel chạy ở luồng nền; giao diện hiển thị từng bước YOLO, OCR, tra cứu nhân viên, lưu ảnh và ghi nhật ký. Ngay sau khi OCR trả kết quả, biển số được hiển thị lớn và mã/tên nhân viên (hoặc trạng thái khách vãng lai/đang xác minh) được cập nhật trước khi lưu ảnh và ghi nhật ký. Nếu một lần OCR kéo dài từ 15 giây, giao diện báo tác vụ đang chậm nhưng không hủy luồng nhận diện. Mỗi lối chia vùng hiển thị theo tỉ lệ 70/30: video chiếm 70%, cột bên phải hiển thị ảnh biển số và vùng xe ước lượng. Video được crop giữa để lấp đầy vùng hiển thị; khi ghi nhận, YOLO/OCR chỉ xử lý vùng crop cùng tỉ lệ với phần video đang thấy. Kết quả OCR được hiển thị lớn bên dưới video. Vùng xe được ước lượng bằng cách mở rộng bounding box biển số, không phải kết quả từ model phát hiện xe riêng.
- **Đối chiếu lượt xe:** khi OCR lượt ra trùng duy nhất biển số của một phiên vào đang mở, hệ thống tự ghép hai lượt, cập nhật nhật ký và hiển thị dấu tick trên ảnh biển số. Nếu không đọc được biển số, không tìm thấy phiên phù hợp hoặc có nhiều phiên trùng, lượt ra được giữ trong hàng đợi thủ công và hiển thị dấu cancel. Mọi lượt vẫn được lưu trong nhật ký; chỉ lượt chờ xác minh/đối chiếu xuất hiện trong hàng đợi. Với lượt thủ công, xem ảnh và chọn phiên vào đang mở, nhập/sửa biển số nếu cần rồi xác nhận.
- **Quản lý lịch sử:** xem nhật ký không thể chỉnh sửa trực tiếp, làm mới hoặc xuất báo cáo Excel/CSV. Nhật ký có trạng thái và đường dẫn ảnh bằng chứng.
- **Quản lý nhân sự:** chọn một dòng để sửa hoặc xóa; dùng biểu mẫu để thêm thông tin nhân viên.

Mỗi lượt ghi nhận lưu ảnh toàn cảnh và các ảnh crop có sẵn tại `captures\YYYY\MM\DD`. Nếu OCR lối vào không đọc được, xe vẫn được ghi nhận là một phiên đang mở với trạng thái `Đang gửi - chờ xác minh`; phiên xuất hiện trong cả danh sách lượt cần xác minh và danh sách xe đang ở bãi. Xác nhận thủ công sẽ cập nhật biển số, loại xe và mã nhân viên mà không tạo phiên thứ hai. Khi chuyển dự án hoặc sao lưu dữ liệu, hãy giữ `staff.xlsx`, `parking_logs.xlsx` và thư mục `captures`; workbook nhân sự được mã hóa bằng cùng mật khẩu Admin và cần mật khẩu đó để mở trực tiếp. Mật khẩu mặc định `123` được lưu trong mã nguồn nên chỉ phù hợp hạn chế việc mở file trực tiếp, không phải bảo vệ mạnh trước người có quyền truy cập mã nguồn hoặc máy tính. Thư mục ảnh bị loại khỏi Git vì có thể chứa hình ảnh nhận dạng cá nhân. Các nhật ký cũ được giữ nguyên nhưng không có mã phiên/ảnh để ghép ngược với lượt mới.

## Model nhận diện biển số

Ứng dụng dùng YOLOv8n đã huấn luyện để cắt vùng biển số trước khi chuyển ảnh nhỏ đó cho PaddleOCR. Checkpoint YOLO được đóng gói tại `models\license_plate_yolov8n.pt` và nạp theo đường dẫn tương đối với mã nguồn, không phụ thuộc vị trí cài dự án. Khi chuyển dự án sang máy khác, hãy mang theo thư mục `models`. Có thể ghi đè vị trí model bằng biến môi trường `PARKING_PLATE_MODEL`. Đường dẫn `weights\ultralytics\yolov8\yolov8n\yolov8n.pt` là weights COCO gốc, không dùng để định vị biển số; ứng dụng sẽ từ chối model này.

Khi mở ứng dụng, YOLO và PaddleOCR được nạp/làm nóng trong luồng nền; ảnh biển số chỉ chạy qua YOLO rồi OCR trên vùng đã cắt. YOLO tự dùng CUDA nếu PyTorch phát hiện GPU NVIDIA khả dụng, nếu không chạy CPU với số luồng giới hạn để tránh tranh chấp tài nguyên. OCR dùng model PaddleOCR v6 tiny, không chạy phân loại hướng dòng chữ, giới hạn phát hiện chữ trên crop còn 256 px; nếu không đọc được thì thử lại một lần ở 384 px. Backend Paddle tiêu chuẩn trên CPU được chọn, MKLDNN tắt để tránh lỗi PIR/oneDNN.

Thời gian nhận diện được hiển thị sau mỗi lượt. Benchmark trên máy phát triển (Ryzen 5 7535HS, CPU) với model đã làm nóng: YOLOv8n khoảng 0,05 giây/lượt; PaddleOCR v6 tiny đọc ảnh crop biển số tổng hợp 380×120 trong khoảng 0,28 giây; toàn pipeline nhận đúng `60F364435` trong khoảng 0,25 giây, còn luồng ghi nhận đầy đủ gồm Excel khoảng 0,36 giây trên ảnh ghép validation 1920×1920. Đây là ảnh validation, không phải video trực tiếp ở cổng; cần kiểm tra thêm với camera thật. Model tiny ưu tiên tốc độ; nếu nhận diện không đủ chính xác, đổi model OCR cỡ nhỏ/medium và chấp nhận tăng độ trễ.

Checkpoint YOLO hiện nằm trong thư mục dự án. Nếu đưa dự án lên GitHub hoặc phân phối cho máy khác, chỉ chia sẻ checkpoint khi bạn có quyền phân phối model và dữ liệu huấn luyện đó. PaddleOCR là model riêng và vẫn cần được tải ở lần nhận diện đầu tiên như hướng dẫn cài đặt.

### Nếu đang dùng Python 3.14

PaddlePaddle chưa có gói Windows cho Python 3.14. Cài Python 3.13 bản 64-bit và làm theo các lệnh cài đặt ở trên; trong VS Code, chọn interpreter `.venv\Scripts\python.exe` bằng lệnh **Python: Select Interpreter**.

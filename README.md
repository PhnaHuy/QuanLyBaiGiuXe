# Quản lý bãi giữ xe thông minh

Ứng dụng desktop Windows viết bằng Python, giao diện tiếng Việt, dùng PySide6, OpenCV, Pandas và Openpyxl. Dữ liệu được lưu trong hai tệp Excel cạnh chương trình: `staff.xlsx` và `parking_logs.xlsx`.

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

Hai tệp Excel mẫu sẽ được tạo tự động khi khởi động lần đầu. Hãy đóng các tệp này trong Microsoft Excel trước khi ứng dụng ghi dữ liệu.

## Sử dụng

- **Điều hành:** nhập chỉ số webcam (ví dụ `0`, `1`) hoặc chọn tệp video, bấm **Mở nguồn**, sau đó bấm nút ghi nhận tương ứng. Nhận diện và ghi Excel chạy ở luồng nền.
- **Quản lý lịch sử:** xem nhật ký không thể chỉnh sửa trực tiếp, làm mới hoặc xuất báo cáo Excel/CSV.
- **Quản lý nhân sự:** chọn một dòng để sửa hoặc xóa; dùng biểu mẫu để thêm thông tin nhân viên.

## Model nhận diện biển số

Ứng dụng dùng YOLOv8n đã huấn luyện để cắt vùng biển số trước khi chuyển ảnh nhỏ đó cho PaddleOCR. Checkpoint YOLO được đóng gói tại `models\license_plate_yolov8n.pt` và nạp theo đường dẫn tương đối với mã nguồn, không phụ thuộc vị trí cài dự án. Khi chuyển dự án sang máy khác, hãy mang theo thư mục `models`. Có thể ghi đè vị trí model bằng biến môi trường `PARKING_PLATE_MODEL`. Đường dẫn `weights\ultralytics\yolov8\yolov8n\yolov8n.pt` là weights COCO gốc, không dùng để định vị biển số; ứng dụng sẽ từ chối model này.

Khi mở ứng dụng, YOLO và PaddleOCR được nạp/làm nóng trong luồng nền; ảnh biển số chỉ chạy qua YOLO rồi OCR trên vùng đã cắt. YOLO tự dùng CUDA nếu PyTorch phát hiện GPU NVIDIA khả dụng, nếu không chạy CPU với số luồng giới hạn để tránh tranh chấp tài nguyên. OCR dùng model PaddleOCR v6 tiny, không chạy phân loại hướng dòng chữ, giới hạn phát hiện chữ trên crop còn 256 px; nếu không đọc được thì thử lại một lần ở 384 px. Backend Paddle tiêu chuẩn trên CPU được chọn, MKLDNN tắt để tránh lỗi PIR/oneDNN.

Thời gian nhận diện được hiển thị sau mỗi lượt. Benchmark trên máy phát triển (Ryzen 5 7535HS, CPU) với model đã làm nóng: YOLOv8n khoảng 0,05 giây/lượt; PaddleOCR v6 tiny đọc ảnh crop biển số tổng hợp 380×120 trong khoảng 0,28 giây; toàn pipeline nhận đúng `60F364435` trong khoảng 0,25 giây, còn luồng ghi nhận đầy đủ gồm Excel khoảng 0,36 giây trên ảnh ghép validation 1920×1920. Đây là ảnh validation, không phải video trực tiếp ở cổng; cần kiểm tra thêm với camera thật. Model tiny ưu tiên tốc độ; nếu nhận diện không đủ chính xác, đổi model OCR cỡ nhỏ/medium và chấp nhận tăng độ trễ.

Checkpoint YOLO hiện nằm trong thư mục dự án. Nếu đưa dự án lên GitHub hoặc phân phối cho máy khác, chỉ chia sẻ checkpoint khi bạn có quyền phân phối model và dữ liệu huấn luyện đó. PaddleOCR là model riêng và vẫn cần được tải ở lần nhận diện đầu tiên như hướng dẫn cài đặt.

### Nếu đang dùng Python 3.14

PaddlePaddle chưa có gói Windows cho Python 3.14. Cài Python 3.13 bản 64-bit và làm theo các lệnh cài đặt ở trên; trong VS Code, chọn interpreter `.venv\Scripts\python.exe` bằng lệnh **Python: Select Interpreter**.

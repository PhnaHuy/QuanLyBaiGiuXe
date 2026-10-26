# Quản lý bãi giữ xe thông minh

Ứng dụng desktop Windows viết bằng Python, giao diện tiếng Việt, dùng PySide6, OpenCV, Pandas và Openpyxl. Dữ liệu được lưu trong hai tệp Excel cạnh chương trình: `staff.xlsx` và `parking_logs.xlsx`.

## Cài đặt

1. Cài Python 3.10 trở lên.
2. Mở PowerShell tại thư mục `QuanLyBaiGiuXe` và chạy:

   ```powershell
   py -m pip install -r requirements.txt
   ```

3. Cài Tesseract OCR cho Windows và bảo đảm chương trình `tesseract.exe` nằm trong `PATH`. Nếu chưa cài hoặc không tìm thấy, ứng dụng sẽ báo rõ khi nhận diện.
4. Khởi chạy:

   ```powershell
   py main.py
   ```

Hai tệp Excel mẫu sẽ được tạo tự động khi khởi động lần đầu. Hãy đóng các tệp này trong Microsoft Excel trước khi ứng dụng ghi dữ liệu.

## Sử dụng

- **Điều hành:** nhập chỉ số webcam (ví dụ `0`, `1`) hoặc chọn tệp video, bấm **Mở nguồn**, sau đó bấm nút ghi nhận tương ứng. Nhận diện và ghi Excel chạy ở luồng nền.
- **Quản lý lịch sử:** xem nhật ký không thể chỉnh sửa trực tiếp, làm mới hoặc xuất báo cáo Excel/CSV.
- **Quản lý nhân sự:** chọn một dòng để sửa hoặc xóa; dùng biểu mẫu để thêm thông tin nhân viên.

OCR dùng Tesseract với tiền xử lý ảnh cơ bản. Chất lượng nhận diện phụ thuộc vào độ phân giải, ánh sáng, góc chụp và việc biển số có nằm rõ trong khung hình hay không.

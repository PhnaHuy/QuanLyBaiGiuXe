# Tài liệu phân tích hệ thống quản lý bãi giữ xe

## 1. Tổng quan

### 1.1. Mục đích

Hệ thống là ứng dụng desktop chạy trên Windows, hỗ trợ nhân viên vận hành ghi nhận lượt xe tại lối vào và lối ra. Ứng dụng lấy hình ảnh từ webcam hoặc tệp video, nhận diện biển số tự động, tra cứu biển số trong danh sách nhân viên, sau đó lưu lượt xe và cung cấp chức năng xem, xuất lịch sử.

### 1.2. Phạm vi chức năng

Hệ thống hiện có ba nhóm chức năng:

1. **Điều hành:** mở nguồn hình ảnh cho lối vào/lối ra, xem hình trực tiếp và chụp khung hình để nhận diện, ghi nhận lượt xe.
2. **Quản lý lịch sử:** xem nhật ký lượt xe và xuất báo cáo ra Excel hoặc CSV.
3. **Quản lý nhân sự:** xem, thêm, sửa và xóa thông tin nhân viên cùng biển số xe được gán.

Đây là ứng dụng đơn máy, dữ liệu lưu trong các tệp Excel bên cạnh mã nguồn. Hệ thống chưa có máy chủ trung tâm, tài khoản hoặc phân quyền người dùng, xử lý thanh toán, nhận diện khuôn mặt, hoặc cơ chế tự động đối chiếu lượt vào–ra.

### 1.3. Thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| Lượt xe | Một lần người vận hành chụp khung hình và hệ thống nhận diện, ghi một dòng nhật ký. |
| Lối vào / lối ra | Hai khu vực thao tác riêng trên màn hình điều hành; mỗi khu vực có nguồn hình ảnh và nút ghi nhận riêng. |
| Nhân viên | Xe có biển số khớp với biển số đã khai báo trong danh sách nhân viên. |
| Khách vãng lai | Xe có biển số không khớp với danh sách nhân viên. |
| Model YOLO | Model phát hiện vùng biển số trong ảnh. |
| PaddleOCR | Thành phần đọc ký tự trên vùng biển số do YOLO cắt ra. |

## 2. Tác nhân

| Tác nhân | Vai trò và mục tiêu | Tương tác với hệ thống |
|---|---|---|
| Nhân viên bảo vệ / vận hành | Theo dõi hình ảnh tại lối vào hoặc lối ra và ghi nhận xe khi cần. | Mở webcam hoặc chọn video, xem khung hình, chụp và ghi nhận, xem kết quả hoặc thông báo lỗi. |
| Nhân viên quản lý bãi xe | Quản lý dữ liệu nhân viên, kiểm tra nhật ký và tạo báo cáo. | Thêm/sửa/xóa hồ sơ nhân viên; xem/làm mới lịch sử; xuất Excel hoặc CSV. |
| Nhân viên gửi xe | Đối tượng được nhận diện khi biển số khớp với hồ sơ nhân viên. | Không thao tác trực tiếp trên phần mềm; hồ sơ của họ được nhân viên quản lý khai báo. |
| Khách vãng lai | Đối tượng có xe không khớp danh sách nhân viên. | Không thao tác trực tiếp; lượt xe được nhân viên vận hành ghi nhận. |
| Webcam / tệp video | Nguồn ảnh đầu vào cho chức năng điều hành. | Cung cấp các khung hình để hiển thị và chụp nhận diện. |
| Model nhận diện | Thành phần kỹ thuật phát hiện và đọc biển số. | YOLO xác định vùng biển số; PaddleOCR đọc ký tự từ vùng cắt. |

Các vai trò người dùng trong bảng là vai trò nghiệp vụ, không phải tài khoản đăng nhập. Phiên bản hiện tại không xác thực danh tính hay phân quyền thao tác.

## 3. User Story

### US-01 — Mở nguồn hình ảnh

**Là** nhân viên vận hành, **tôi muốn** kết nối webcam hoặc chọn tệp video cho từng lối, **để** quan sát hình ảnh phương tiện trước khi ghi nhận.

**Điều kiện chấp nhận**

- Có thể nhập chỉ số webcam (ví dụ `0`, `1`) hoặc chọn tệp video được hỗ trợ.
- Hệ thống hiển thị các khung hình nhận được trên khu vực tương ứng.
- Nếu không mở được webcam/tệp hoặc không nhận được khung hình, hệ thống thông báo lỗi.
- Khi video chạy đến cuối, hệ thống hiển thị trạng thái video đã kết thúc.

### US-02 — Nhận diện và ghi nhận một lượt xe

**Là** nhân viên vận hành, **tôi muốn** chụp khung hình ở lối đang thao tác và ghi nhận lượt xe, **để** lưu biển số cùng thời gian và phân loại phương tiện.

**Điều kiện chấp nhận**

- Không cho ghi nhận khi nguồn chưa chạy hoặc chưa có khung hình.
- Hệ thống phát hiện vùng biển số bằng YOLO, sau đó dùng PaddleOCR để đọc ký tự.
- Biển số được chuẩn hóa trước khi kiểm tra định dạng và tra cứu hồ sơ nhân viên.
- Nếu biển số khớp hồ sơ, lượt xe được ghi loại `Nhân viên` cùng mã nhân viên; nếu không khớp, loại là `Khách vãng lai`.
- Bản ghi có thời gian, biển số, lối, loại xe và mã nhân viên (để trống với khách vãng lai).
- Giao diện hiển thị kết quả và thời gian nhận diện; nếu không đọc được biển số hoặc không ghi được dữ liệu thì thông báo lỗi.

### US-03 — Xem lịch sử lượt xe

**Là** nhân viên quản lý, **tôi muốn** xem danh sách các lượt xe đã ghi nhận, **để** tra cứu hoạt động của bãi xe.

**Điều kiện chấp nhận**

- Bảng lịch sử hiển thị các trường `Thời gian`, `Biển số`, `Cổng`, `Loại xe`, `Mã nhân viên`.
- Bảng chỉ đọc; người dùng có thể làm mới dữ liệu.
- Lỗi đọc tệp hoặc thiếu cột bắt buộc được thông báo trên giao diện.

### US-04 — Xuất báo cáo lịch sử

**Là** nhân viên quản lý, **tôi muốn** xuất nhật ký ra Excel hoặc CSV, **để** lưu trữ hoặc xử lý báo cáo bên ngoài.

**Điều kiện chấp nhận**

- Người dùng chọn vị trí lưu và định dạng Excel (`.xlsx`) hoặc CSV (`.csv`).
- Nếu chưa nhập phần mở rộng, hệ thống dùng định dạng đang chọn trong hộp thoại lưu.
- Hệ thống thông báo xuất thành công hoặc nêu lỗi khi không thể tạo tệp, chẳng hạn tệp bị khóa.

### US-05 — Xem danh sách nhân viên

**Là** nhân viên quản lý, **tôi muốn** xem danh sách nhân viên và biển số xe đã gán, **để** kiểm tra dữ liệu dùng phân loại phương tiện.

**Điều kiện chấp nhận**

- Danh sách thể hiện mã nhân viên, tên nhân viên và biển số xe.
- Chọn một dòng sẽ đưa dữ liệu nhân viên vào biểu mẫu để sửa hoặc xóa.
- Bảng không cho chỉnh sửa trực tiếp.

### US-06 — Thêm nhân viên

**Là** nhân viên quản lý, **tôi muốn** thêm hồ sơ nhân viên gồm mã, tên và biển số, **để** hệ thống nhận biết xe nhân viên.

**Điều kiện chấp nhận**

- Cả ba trường đều bắt buộc.
- Mã nhân viên không được trùng; biển số sau khi chuẩn hóa không được gán cho nhân viên khác.
- Khi thành công, danh sách được tải lại và biểu mẫu được xóa trắng.
- Khi dữ liệu không hợp lệ hoặc tệp Excel không ghi được, hệ thống hiển thị lý do.

### US-07 — Cập nhật nhân viên

**Là** nhân viên quản lý, **tôi muốn** cập nhật thông tin nhân viên đã chọn, **để** dữ liệu hồ sơ luôn chính xác.

**Điều kiện chấp nhận**

- Phải chọn một nhân viên trước khi cập nhật.
- Các quy tắc bắt buộc và không trùng mã/biển số vẫn được áp dụng.
- Nếu hồ sơ không còn tồn tại hoặc dữ liệu không hợp lệ, thao tác bị từ chối và người dùng được thông báo.

### US-08 — Xóa nhân viên

**Là** nhân viên quản lý, **tôi muốn** xóa hồ sơ nhân viên đã chọn sau khi xác nhận, **để** loại bỏ thông tin không còn sử dụng.

**Điều kiện chấp nhận**

- Phải chọn hồ sơ trước khi xóa.
- Hệ thống yêu cầu xác nhận; lựa chọn không đồng ý sẽ hủy thao tác.
- Sau khi xóa thành công, danh sách được làm mới và biểu mẫu được xóa trắng.
- Việc xóa hồ sơ không xóa hay sửa các lượt xe lịch sử đã ghi.

### US-09 — Khởi tạo model nhận diện

**Là** nhân viên vận hành, **tôi muốn** ứng dụng nạp và làm nóng model trong nền khi mở chương trình, **để** chức năng nhận diện sẵn sàng mà giao diện không phải tự tải model khi thao tác.

**Điều kiện chấp nhận**

- YOLO được nạp từ `models\license_plate_yolov8n.pt` trong dự án, trừ khi có cấu hình ghi đè.
- PaddleOCR được khởi tạo và có thể cần tải model ở lần chạy đầu.
- Trạng thái sẵn sàng hoặc lỗi khởi tạo được hiển thị cho người dùng.

## 4. Mô hình phân chia module

### 4.1. Sơ đồ module

```text
┌────────────────────────────────────────────────────────┐
│ main.py — Điểm khởi chạy ứng dụng                      │
│ Tạo QApplication, khởi tạo dữ liệu và mở MainWindow    │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────▼─────────────┐
             │ ui.py — Giao diện và điều phối │
             │ MainWindow, GatePanel, workers │
             └──────┬───────────┬─────────┘
                    │           │
       ┌────────────▼───┐   ┌───▼────────────────┐
       │ camera_thread.py│   │ anpr.py             │
       │ Đọc webcam/video│   │ YOLO + PaddleOCR    │
       └────────────────┘   └─────────┬──────────┘
                                      │
                         ┌────────────▼───────────┐
                         │ excel_db.py             │
                         │ Nghiệp vụ dữ liệu Excel│
                         └────────────┬───────────┘
                                      │
                         ┌────────────▼───────────┐
                         │ staff.xlsx             │
                         │ parking_logs.xlsx      │
                         └────────────────────────┘

Model YOLO: models\license_plate_yolov8n.pt
Model OCR: PaddleOCR quản lý/tải theo cấu hình thư viện
```

### 4.2. Trách nhiệm từng module

| Module / thành phần | Trách nhiệm | Thành phần chính |
|---|---|---|
| `main.py` | Điểm vào ứng dụng; tạo Qt Application, khởi tạo Excel và mở cửa sổ chính. Nếu không chuẩn bị được dữ liệu, hiển thị lỗi khởi động. | `main()` |
| `ui.py` | Giao diện, điều phối luồng thao tác, gọi lớp dữ liệu và pipeline nhận diện; hiển thị kết quả/lỗi. | `MainWindow`, `GatePanel`, `RecognitionWorker`, `ModelWarmupWorker` |
| `camera_thread.py` | Đọc khung hình từ OpenCV trong luồng nền, giữ bản sao khung hình mới nhất và phát tín hiệu cập nhật giao diện. | `CameraThread` |
| `anpr.py` | Nạp model, phát hiện/cắt vùng biển số, nhận dạng OCR, chuẩn hóa và chọn kết quả phù hợp. | `initialize_models()`, `recognize_plate()`, `normalize_plate()` |
| `excel_db.py` | Tạo/đọc/ghi tệp Excel; kiểm tra dữ liệu nhân viên, phát hiện trùng và tra cứu theo biển số. | `ExcelDatabase` |
| `models\license_plate_yolov8n.pt` | Checkpoint YOLO đã huấn luyện phát hiện biển số, được đóng gói cùng dự án. | Model nhị phân |
| `staff.xlsx` | Lưu hồ sơ nhân viên. Tự tạo khi chưa có. | Mã nhân viên, tên nhân viên, biển số xe |
| `parking_logs.xlsx` | Lưu lịch sử lượt xe. Tự tạo khi chưa có. | Thời gian, biển số, cổng, loại xe, mã nhân viên |

### 4.3. Luồng dữ liệu nhận diện

1. Nhân viên mở nguồn hình ảnh ở một trong hai bảng điều hành.
2. `CameraThread` đọc khung hình và phát hình ảnh để giao diện hiển thị; đồng thời lưu khung hình mới nhất để thao tác chụp.
3. Khi người dùng chọn **Chụp & Ghi nhận**, `GatePanel` lấy bản sao khung hình và khởi chạy `RecognitionWorker`.
4. `recognize_plate()` dùng YOLO định vị tối đa ba vùng biển số theo độ tin cậy, cắt vùng ảnh và chuyển vùng cắt sang PaddleOCR.
5. Kết quả OCR được chuẩn hóa và kiểm tra theo định dạng biển số. Nếu cần, các đoạn ký tự gần nhau trên cùng vùng có thể được ghép thành ứng viên.
6. `RecognitionWorker` tra cứu biển số trong `staff.xlsx`, phân loại nhân viên/khách vãng lai và tạo thời gian ghi nhận.
7. `ExcelDatabase` thêm bản ghi vào `parking_logs.xlsx`.
8. Worker phát kết quả hoặc lỗi về giao diện; giao diện cập nhật trạng thái và bật lại nút ghi nhận.

Các thao tác đọc camera, nhận diện và làm nóng model chạy trong QThread để hạn chế chặn giao diện. Truy cập model được bảo vệ bằng khóa; thao tác dữ liệu Excel được đồng bộ trong `ExcelDatabase`.

### 4.4. Luồng khởi động và lưu trữ

- Ứng dụng lấy thư mục chứa mã nguồn làm thư mục dữ liệu.
- `ExcelDatabase.initialize()` tạo `staff.xlsx` và `parking_logs.xlsx` với các tiêu đề cần thiết nếu tệp chưa tồn tại.
- Cửa sổ chính được mở sau khi khởi tạo dữ liệu.
- Model nhận diện được nạp/làm nóng trong worker riêng. Model YOLO mặc định ở thư mục dự án; biến `PARKING_PLATE_MODEL` có thể ghi đè đường dẫn.
- Tệp Excel đang mở hoặc bị khóa có thể khiến thao tác đọc/ghi thất bại; ứng dụng đưa ra thông báo yêu cầu đóng tệp.

## 5. Chức năng hệ thống

### 5.1. Điều hành lối vào và lối ra

- Mỗi lối có một bảng riêng, nguồn mặc định là webcam chỉ số `0` cho lối vào và `1` cho lối ra.
- Người dùng có thể nhập chỉ số webcam hoặc chọn tệp video.
- Hình ảnh được hiển thị liên tục khi nguồn hoạt động.
- Người dùng chủ động chụp khung hình để nhận diện; hệ thống không tự động nhận diện mọi khung hình.
- Mỗi lượt nhận diện được xử lý nền, không cho chạy hai lần ghi nhận đồng thời trên cùng bảng khi worker trước còn hoạt động.
- Kết quả nêu biển số, lối, loại đối tượng, mã/tên nhân viên nếu có và thời gian nhận diện.

### 5.2. Nhận diện biển số

- YOLO phát hiện vùng biển số; checkpoint mặc định là `models\license_plate_yolov8n.pt`.
- PaddleOCR đọc ký tự trên ảnh biển số đã cắt.
- Chuỗi nhận diện được chuyển chữ hoa và loại bỏ ký tự không phải chữ/số để chuẩn hóa, dùng cho kiểm tra định dạng và tra cứu hồ sơ.
- Nếu không phát hiện biển số, OCR không đọc được hoặc model không khởi tạo được, hệ thống trả lỗi thay vì ghi lượt xe không có biển số hợp lệ.
- PaddleOCR có thể cần Internet ở lần đầu để tải model theo cấu hình thư viện.

### 5.3. Quản lý lịch sử

- Hiển thị các bản ghi trong `parking_logs.xlsx`.
- Tải lại dữ liệu khi mở tab hoặc nhấn **Làm mới**.
- Lịch sử chỉ đọc trên giao diện; hiện chưa có chức năng sửa/xóa, lọc hoặc tìm kiếm.
- Xuất toàn bộ dữ liệu lịch sử ra `.xlsx` hoặc `.csv`.

### 5.4. Quản lý nhân sự

- Hiển thị danh sách trong `staff.xlsx`.
- Thêm hồ sơ với đủ mã nhân viên, tên và biển số.
- Sửa hồ sơ đang chọn; xóa hồ sơ sau khi xác nhận.
- Không chấp nhận mã nhân viên trùng hoặc biển số trùng sau chuẩn hóa.
- Tra cứu hồ sơ nhân viên bằng biển số đã chuẩn hóa.
- Khi xóa nhân viên, lịch sử lượt xe cũ được giữ nguyên; các lượt sau đó với biển số không còn trong danh sách sẽ được phân loại là khách vãng lai.

### 5.5. Khởi tạo và xử lý lỗi

- Khởi động thất bại nếu không thể chuẩn bị dữ liệu Excel; người dùng nhận hộp thoại nêu nguyên nhân.
- Lỗi nguồn hình ảnh, lỗi model, ảnh không hợp lệ, không phát hiện/đọc được biển số và lỗi đọc/ghi Excel được báo trên giao diện.
- Dữ liệu nhân viên bị thiếu cột bắt buộc sẽ được báo lỗi khi đọc.

## 6. Mô hình dữ liệu

### 6.1. Hồ sơ nhân viên — `staff.xlsx`

| Trường | Ý nghĩa | Quy tắc |
|---|---|---|
| `Mã nhân viên` | Mã định danh nhân viên trong danh sách. | Bắt buộc, không trùng. |
| `Tên nhân viên` | Tên hiển thị của nhân viên. | Bắt buộc. |
| `Biển số xe` | Biển số dùng để nhận diện xe nhân viên. | Bắt buộc, không trùng sau chuẩn hóa. |

### 6.2. Nhật ký lượt xe — `parking_logs.xlsx`

| Trường | Ý nghĩa |
|---|---|
| `Thời gian` | Thời điểm ghi nhận theo thời gian hệ thống, định dạng `YYYY-MM-DD HH:MM:SS`. |
| `Biển số` | Biển số hệ thống nhận diện được. |
| `Cổng` | Tên lối đang thao tác (`Vào` hoặc `Ra`). |
| `Loại xe` | `Nhân viên` nếu biển số khớp hồ sơ; nếu không thì `Khách vãng lai`. |
| `Mã nhân viên` | Mã hồ sơ khớp; để trống với khách vãng lai. |

Nhật ký hiện không lưu ảnh chụp, tên nhân viên, mã lượt xe riêng, trạng thái thanh toán hay quan hệ tham chiếu tường minh giữa hai lượt vào/ra.

## 7. Quy tắc nghiệp vụ và giới hạn

1. Một lượt chỉ được ghi khi đã có nguồn chạy và khung hình hợp lệ.
2. Việc ghi nhận do nhân viên vận hành kích hoạt bằng nút bấm, không diễn ra tự động theo chuyển động hoặc phát hiện phương tiện.
3. Phân loại nhân viên dựa trên đối sánh biển số với danh sách nhân viên; không có quy trình xác minh danh tính khác.
4. Nhật ký ghi nhận từng lần tại một lối độc lập. Hệ thống hiện không bắt buộc xe phải có lượt vào trước lượt ra và không tính thời lượng gửi xe.
5. Hai bảng điều hành cho phép chọn nguồn riêng, nhưng hệ thống không xác thực đó là vị trí vào/ra vật lý tương ứng.
6. Excel là kho dữ liệu cục bộ; không hỗ trợ nhiều máy cùng ghi dữ liệu an toàn qua mạng.
7. Báo cáo xuất toàn bộ nhật ký, chưa có lọc theo ngày, cổng, biển số hoặc loại xe.
8. Người dùng thao tác trong ứng dụng không cần đăng nhập; mọi người dùng máy có thể truy cập các chức năng hiện có.

## 8. Đặc tính kỹ thuật liên quan

- **Nền tảng:** ứng dụng desktop Python trên Windows, giao diện PySide6.
- **Xử lý ảnh:** OpenCV đọc webcam/video; YOLO phát hiện biển số; PaddleOCR đọc ký tự.
- **Lưu trữ:** Excel qua Pandas và Openpyxl.
- **Xử lý đồng thời:** QThread cho camera, nhận diện và làm nóng model; khóa bảo vệ các thao tác dùng chung.
- **Khả năng di chuyển:** checkpoint YOLO nằm trong thư mục dự án và được định vị dựa trên vị trí mã nguồn. Khi chuyển dự án, cần mang theo thư mục `models`; PaddleOCR có thể cần tải model riêng ở lần chạy đầu.
- **Phụ thuộc vận hành:** máy cần cài các gói trong `requirements.txt`; cần quyền truy cập webcam/tệp video và quyền đọc/ghi thư mục dự án.

from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import cv2
import pandas as pd
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QImage, QPalette, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from anpr import ANPRError, initialize_models, normalize_plate, recognize_plate
from camera_thread import CameraThread, crop_frame_to_aspect
from excel_db import ExcelDatabase, ExcelDatabaseError
from image_store import CaptureStorage, CaptureStorageError


DASHBOARD_STYLESHEET = """
QWidget {
    color: #172b4d;
}
QMainWindow, QWidget#dashboardRoot {
    background-color: #f3f6fb;
    color: #172b4d;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel {
    color: #344563;
}
QLabel#pageTitle {
    color: #172b4d;
    font-size: 20pt;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #6b778c;
    font-size: 9pt;
}
QLabel#sectionEyebrow {
    color: #6b778c;
    font-size: 8pt;
    font-weight: 700;
}
QLabel#modelStatus {
    background-color: #fff7e6;
    color: #8a6116;
    border: 1px solid #ffe2a8;
    border-radius: 12px;
    padding: 7px 12px;
    font-weight: 600;
}
QLabel#modelStatus[ready="true"] {
    background-color: #e7f6ec;
    color: #26734d;
    border-color: #b7e4c7;
}
QLabel#modelStatus[ready="false"] {
    background-color: #fff0ef;
    color: #b42318;
    border-color: #ffd1cc;
}
QTabWidget::pane {
    background-color: #f3f6fb;
    border: none;
    top: -1px;
}
QTabBar {
    background-color: transparent;
}
QTabBar::tab {
    background-color: transparent;
    color: #63728a;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 13px 18px 11px;
    margin-right: 4px;
    font-weight: 600;
}
QTabBar::tab:hover {
    color: #175cd3;
    background-color: #eaf1fb;
}
QTabBar::tab:selected {
    color: #175cd3;
    border-bottom-color: #2e6bd1;
}
QGroupBox {
    background-color: #ffffff;
    color: #172b4d;
    border: 1px solid #e1e7f0;
    border-radius: 10px;
    margin-top: 12px;
    padding: 16px 14px 14px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 5px;
    color: #344563;
    background-color: #ffffff;
}
QWidget#controlSurface, QWidget#previewSurface {
    background-color: #f8fafd;
    border: 1px solid #e6ebf2;
    border-radius: 8px;
}
QWidget#tabPage {
    background-color: #f3f6fb;
}
QLineEdit {
    background-color: #ffffff;
    color: #172b4d;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #2e6bd1;
    min-height: 20px;
}
QLineEdit:hover {
    border-color: #98a9c1;
}
QLineEdit:focus {
    border: 1px solid #2e6bd1;
}
QPushButton {
    background-color: #ffffff;
    color: #344563;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 13px;
    min-height: 20px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #f5f8fc;
    border-color: #98a9c1;
}
QPushButton:pressed {
    background-color: #e9eef6;
}
QPushButton:disabled {
    background-color: #f1f3f6;
    color: #98a1ae;
    border-color: #e1e5eb;
}
QPushButton[variant="primary"] {
    background-color: #245fcb;
    color: #ffffff;
    border-color: #245fcb;
}
QPushButton[variant="primary"]:hover {
    background-color: #194eae;
    border-color: #194eae;
}
QPushButton[variant="success"] {
    background-color: #238653;
    color: #ffffff;
    border-color: #238653;
}
QPushButton[variant="success"]:hover {
    background-color: #196e42;
    border-color: #196e42;
}
QPushButton[variant="danger"] {
    color: #b42318;
    border-color: #f0c4c0;
}
QPushButton[variant="danger"]:hover {
    background-color: #fff0ef;
}
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f7f9fc;
    color: #344563;
    border: 1px solid #e1e7f0;
    border-radius: 7px;
    gridline-color: #edf0f5;
    selection-background-color: #e8f0fe;
    selection-color: #174ea6;
    outline: none;
}
QHeaderView::section {
    background-color: #f3f6fb;
    color: #52637a;
    border: none;
    border-bottom: 1px solid #e1e7f0;
    padding: 9px 8px;
    font-weight: 700;
}
QStatusBar {
    background-color: #ffffff;
    color: #63728a;
    border-top: 1px solid #e1e7f0;
}
QDialog, QMessageBox {
    background-color: #ffffff;
    color: #172b4d;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QDialog QLabel, QMessageBox QLabel {
    background-color: transparent;
    color: #172b4d;
}
QDialog QLineEdit, QDialog QComboBox {
    background-color: #ffffff;
    color: #172b4d;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 9px;
}
QDialog QPushButton, QMessageBox QPushButton {
    min-width: 84px;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #c8d1df;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
    border: none;
}
"""


def configure_light_theme(application):
    palette = application.palette()
    colors = {
        QPalette.ColorRole.Window: "#f3f6fb",
        QPalette.ColorRole.WindowText: "#172b4d",
        QPalette.ColorRole.Base: "#ffffff",
        QPalette.ColorRole.AlternateBase: "#f7f9fc",
        QPalette.ColorRole.Text: "#172b4d",
        QPalette.ColorRole.Button: "#ffffff",
        QPalette.ColorRole.ButtonText: "#172b4d",
        QPalette.ColorRole.ToolTipBase: "#ffffff",
        QPalette.ColorRole.ToolTipText: "#172b4d",
        QPalette.ColorRole.PlaceholderText: "#748198",
        QPalette.ColorRole.Highlight: "#2e6bd1",
        QPalette.ColorRole.HighlightedText: "#ffffff",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    application.setPalette(palette)
    application.setStyleSheet(DASHBOARD_STYLESHEET)


ADMIN_ROLE = "Admin"
EMPLOYEE_ROLE = "Nhân viên"
ADMIN_DEFAULT_PASSWORD = "123"


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đăng nhập hệ thống")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.selected_role = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Xác thực truy cập")
        title.setStyleSheet(
            "color: #172b4d; font-size: 16pt; font-weight: 700;"
        )
        subtitle = QLabel("Chọn vai trò để tiếp tục vào hệ thống.")
        subtitle.setStyleSheet("color: #6b778c;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self.role_combo = QComboBox()
        self.role_combo.addItem("Chọn vai trò...", None)
        self.role_combo.addItem(ADMIN_ROLE, ADMIN_ROLE)
        self.role_combo.addItem(EMPLOYEE_ROLE, EMPLOYEE_ROLE)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Nhập mật khẩu Admin")
        self.password_label = QLabel("Mật khẩu:")
        form.addRow("Vai trò:", self.role_combo)
        form.addRow(self.password_label, self.password_input)
        layout.addLayout(form)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #b42318;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.login_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        self.login_button.setText("Đăng nhập")
        self.login_button.setProperty("variant", "primary")
        self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText("Hủy")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.role_combo.currentIndexChanged.connect(self.update_role_fields)
        self.password_input.returnPressed.connect(self.accept)
        self.update_role_fields()

    def update_role_fields(self):
        is_admin = self.role_combo.currentData() == ADMIN_ROLE
        self.password_label.setVisible(is_admin)
        self.password_input.setVisible(is_admin)
        if not is_admin:
            self.password_input.clear()
        self.error_label.clear()
        self.error_label.hide()

    def accept(self):
        role = self.role_combo.currentData()
        if role is None:
            self.error_label.setText("Vui lòng chọn vai trò đăng nhập.")
            self.error_label.show()
            return
        if (
            role == ADMIN_ROLE
            and self.password_input.text() != ADMIN_DEFAULT_PASSWORD
        ):
            self.error_label.setText("Mật khẩu Admin không chính xác.")
            self.error_label.show()
            self.password_input.selectAll()
            self.password_input.setFocus()
            return
        self.selected_role = role
        super().accept()


class RecognitionWorker(QThread):
    completed = Signal(dict)
    crop_detected = Signal(object, object)
    failed = Signal(str)
    plate_recognized = Signal(str)

    def __init__(self, image, original_image, gate, database, parent=None):
        super().__init__(parent)
        self.image = image
        self.original_image = original_image
        self.gate = gate
        self.database = database

    def run(self):
        recognition_started = perf_counter()
        plate = ""
        plate_crop = None
        vehicle_crop = None
        recognition_error = ""

        def capture_crops(detected_plate, detected_vehicle):
            nonlocal plate_crop, vehicle_crop
            plate_crop = detected_plate
            vehicle_crop = detected_vehicle
            self.crop_detected.emit(plate_crop, vehicle_crop)

        try:
            plate = recognize_plate(self.image, capture_crops)
            self.plate_recognized.emit(plate)
        except ANPRError as error:
            recognition_error = str(error)
        except Exception as error:
            recognition_error = f"Đã xảy ra lỗi khi nhận diện: {error}"

        try:
            recognition_seconds = perf_counter() - recognition_started
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            event_id = uuid4().hex
            storage = CaptureStorage(self.database.directory)
            image_paths = storage.save_capture(
                event_id,
                self.original_image,
                plate_crop,
                vehicle_crop,
            )
            try:
                staff = self.database.find_staff_by_plate(plate) if plate else None
                is_entry = self.gate == "Vào"
                is_recognized_entry = is_entry and bool(plate)
                result = {
                    "Thời gian": timestamp,
                    "Biển số": plate,
                    "Cổng": self.gate,
                    "Loại xe": (
                        "Nhân viên"
                        if staff
                        else "Khách vãng lai"
                        if plate
                        else ""
                    ),
                    "Mã nhân viên": staff["Mã nhân viên"] if staff else "",
                    "Mã lượt": event_id,
                    "Mã phiên": event_id if is_recognized_entry else "",
                    "Trạng thái": (
                        "Đang gửi"
                        if is_recognized_entry
                        else "Chờ xác minh"
                        if is_entry
                        else "Chờ đối chiếu"
                    ),
                    "Biển số OCR": plate,
                    **image_paths,
                    "Tên nhân viên": staff["Tên nhân viên"] if staff else "",
                    "Thời gian nhận diện": recognition_seconds,
                    "Lỗi nhận diện": recognition_error,
                }
                self.database.add_log(result)
            except Exception:
                storage.remove_capture(image_paths)
                raise
        except (CaptureStorageError, ExcelDatabaseError, ValueError) as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(f"Đã xảy ra lỗi khi ghi nhận lượt xe: {error}")
        else:
            self.completed.emit(result)


class ModelWarmupWorker(QThread):
    ready = Signal()
    failed = Signal(str)

    def run(self):
        try:
            initialize_models()
        except ANPRError as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(f"Không thể khởi tạo model nhận diện: {error}")
        else:
            self.ready.emit()


class GatePanel(QGroupBox):
    record_saved = Signal()
    resources_changed = Signal()

    def __init__(self, gate, default_source, database, parent=None):
        super().__init__(f"Lối {gate}", parent)
        self.gate = gate
        self.database = database
        self.camera = None
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(12)

        control_surface = QWidget()
        control_surface.setObjectName("controlSurface")
        control_layout = QVBoxLayout(control_surface)
        control_layout.setContentsMargins(12, 10, 12, 10)
        control_layout.setSpacing(7)
        source_title = QLabel("NGUỒN GIÁM SÁT")
        source_title.setObjectName("sectionEyebrow")
        control_layout.addWidget(source_title)

        source_row = QHBoxLayout()
        source_row.setSpacing(8)
        self.source_input = QLineEdit(default_source)
        self.source_input.setPlaceholderText("Nhập chỉ số webcam hoặc đường dẫn tệp video")
        self.browse_button = QPushButton("Chọn tệp video...")
        self.open_button = QPushButton("Mở nguồn")
        source_row.addWidget(self.source_input, 1)
        source_row.addWidget(self.browse_button)
        source_row.addWidget(self.open_button)
        self.open_button.setProperty("variant", "primary")
        control_layout.addLayout(source_row)
        layout.addWidget(control_surface)

        video_container = QWidget()
        video_layout = QHBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(8)

        self.video_label = QLabel("Chưa mở nguồn hình ảnh")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(0, 0)
        self.video_label.setWordWrap(True)
        self.video_label.setStyleSheet("background-color: #20252b; color: white;")
        video_layout.addWidget(self.video_label, 7)

        preview_panel = QWidget()
        preview_panel.setObjectName("previewSurface")
        preview_panel.setMinimumWidth(0)
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(8)

        self.plate_crop_panel, self.plate_crop_label = self.create_crop_preview(
            "Biển số",
            "Chưa phát hiện biển số",
        )
        self.vehicle_crop_panel, self.vehicle_crop_label = self.create_crop_preview(
            "Xe",
            "Chưa có ảnh xe",
        )
        preview_layout.addWidget(self.plate_crop_panel)
        preview_layout.addWidget(self.vehicle_crop_panel)
        video_layout.addWidget(preview_panel, 3)
        video_layout.setStretch(0, 7)
        video_layout.setStretch(1, 3)
        video_container.setMinimumHeight(270)
        layout.addWidget(video_container, 1)

        self.plate_result_label = QLabel("Chưa có biển số")
        self.plate_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plate_result_label.setMinimumHeight(54)
        self.plate_result_label.setStyleSheet(
            "font-size: 26px; font-weight: bold; color: #175cd3; "
            "background-color: #eef4ff; border: 1px solid #c7d7f5; "
            "border-radius: 8px; padding: 6px;"
        )
        layout.addWidget(self.plate_result_label)

        self.result_label = QLabel("Chưa ghi nhận lượt xe")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("color: #63728a; padding: 2px 4px;")
        self.capture_button = QPushButton(f"Chụp & Ghi nhận Xe {gate}")
        self.capture_button.setProperty("variant", "success")
        self.capture_button.setMinimumHeight(42)
        layout.addWidget(self.result_label)
        layout.addWidget(self.capture_button)

        self.browse_button.clicked.connect(self.choose_video)
        self.open_button.clicked.connect(self.open_source)
        self.capture_button.clicked.connect(self.record_vehicle)

    def choose_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn tệp video",
            "",
            "Tệp video (*.mp4 *.avi *.mov *.mkv);;Tất cả tệp (*.*)",
        )
        if path:
            self.source_input.setText(path)

    def open_source(self):
        value = self.source_input.text().strip()
        if not value:
            QMessageBox.warning(self, "Thiếu nguồn", "Vui lòng nhập chỉ số webcam hoặc chọn tệp video.")
            return

        source = int(value) if value.isdecimal() else value
        if isinstance(source, str) and not Path(source).is_file():
            QMessageBox.warning(self, "Không tìm thấy tệp", "Đường dẫn video không tồn tại.")
            return
        self.stop_camera()
        self.video_label.setText("Đang kết nối nguồn hình ảnh...")
        self.camera = CameraThread(source, self)
        self.camera.khung_hinh_moi.connect(self.show_frame)
        self.camera.loi_nguon.connect(self.show_camera_error)
        self.camera.ket_thuc_nguon.connect(self.show_video_ended)
        self.camera.start()

    def stop_camera(self):
        if self.camera is not None:
            self.camera.dung()
            self.camera.wait()
            self.camera.deleteLater()
            self.camera = None

    def request_camera_stop(self):
        camera = self.camera
        if camera is None:
            return
        camera.finished.connect(self._camera_finished)
        if camera.isRunning():
            camera.dung()
        else:
            self._camera_stopped(camera)

    def _camera_finished(self):
        if self.camera is not None:
            self._camera_stopped(self.camera)

    def _camera_stopped(self, camera):
        if self.camera is camera:
            self.camera = None
            camera.deleteLater()
            self.resources_changed.emit()

    def show_frame(self, image):
        target_size = self.video_label.size()
        if target_size.isEmpty():
            return
        pixmap = QPixmap.fromImage(image).scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x_offset = max(0, (pixmap.width() - target_size.width()) // 2)
        y_offset = max(0, (pixmap.height() - target_size.height()) // 2)
        pixmap = pixmap.copy(
            x_offset,
            y_offset,
            target_size.width(),
            target_size.height(),
        )
        self.video_label.setPixmap(pixmap)

    def show_camera_error(self, message):
        self.video_label.setText(message)
        QMessageBox.warning(self, "Lỗi nguồn hình ảnh", message)

    def show_video_ended(self):
        self.result_label.setText("Video đã phát đến cuối.")

    def record_vehicle(self):
        if self.camera is None or not self.camera.isRunning():
            QMessageBox.warning(self, "Chưa có hình ảnh", "Vui lòng mở nguồn hình ảnh trước khi ghi nhận xe.")
            return
        if self.worker is not None and self.worker.isRunning():
            return
        frame = self.camera.lay_khung_hinh()
        if frame is None:
            QMessageBox.warning(self, "Chưa có hình ảnh", "Nguồn hình ảnh chưa cung cấp được khung hình.")
            return
        try:
            image = crop_frame_to_aspect(
                frame,
                self.video_label.width(),
                self.video_label.height(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Không thể cắt khung hình", str(error))
            return

        self.clear_crop_previews()
        self.plate_result_label.setText("Đang nhận diện...")
        self.capture_button.setEnabled(False)
        self.result_label.setText("Đang nhận diện biển số và ghi dữ liệu...")
        self.worker = RecognitionWorker(
            image,
            frame,
            self.gate,
            self.database,
            self,
        )
        self.worker.crop_detected.connect(self.show_crop_previews)
        self.worker.plate_recognized.connect(self.show_plate_result)
        self.worker.completed.connect(self.show_result)
        self.worker.failed.connect(self.show_record_error)
        self.worker.finished.connect(self.worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    @staticmethod
    def create_crop_preview(title, placeholder):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label = QLabel(placeholder)
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setMinimumWidth(0)
        preview_label.setWordWrap(True)
        preview_label.setMinimumHeight(75)
        preview_label.setStyleSheet(
            "background-color: #f1f4f8; color: #748198; "
            "border: 1px solid #dfe5ed; border-radius: 6px;"
        )
        layout.addWidget(title_label)
        layout.addWidget(preview_label, 1)
        return panel, preview_label

    @staticmethod
    def set_crop_preview(label, crop):
        if crop is None or crop.size == 0:
            return
        rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_crop.shape
        image = QImage(
            rgb_crop.data,
            width,
            height,
            channels * width,
            QImage.Format.Format_RGB888,
        ).copy()
        pixmap = QPixmap.fromImage(image).scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setText("")
        label.setPixmap(pixmap)

    def show_crop_previews(self, plate_crop, vehicle_crop):
        self.set_crop_preview(
            self.plate_crop_label,
            plate_crop,
        )
        self.set_crop_preview(
            self.vehicle_crop_label,
            vehicle_crop,
        )

    def clear_crop_previews(self):
        self.plate_crop_label.clear()
        self.plate_crop_label.setText("Chưa phát hiện biển số")
        self.vehicle_crop_label.clear()
        self.vehicle_crop_label.setText("Chưa có ảnh xe")

    def show_result(self, result):
        plate = result["Biển số"]
        self.show_plate_result(plate)
        employee = result["Mã nhân viên"]
        if employee:
            detail = f'Nhân viên {employee} - {result["Tên nhân viên"]}'
        else:
            detail = "Khách vãng lai"
        if result["Trạng thái"] == "Đang gửi":
            message = (
                f'Đã ghi nhận xe {result["Biển số"]} tại lối {self.gate}. '
                f'{detail}. Ảnh đã được lưu để đối chiếu khi xe ra.'
            )
        else:
            message = (
                f'Lượt xe tại lối {self.gate} đã lưu ảnh và đang chờ đối chiếu. '
                "Mở tab “Đối chiếu lượt xe” để xác minh biển số/ghép lượt."
            )
            if result["Lỗi nhận diện"]:
                message += f' Lỗi nhận diện: {result["Lỗi nhận diện"]}'
        self.result_label.setText(message)
        self.record_saved.emit()

    def show_record_error(self, message):
        if self.plate_result_label.text() == "Đang nhận diện...":
            self.show_plate_result("")
        self.result_label.setText("Không thể ghi nhận lượt xe.")
        QMessageBox.warning(self, "Không thể ghi nhận", message)

    def show_plate_result(self, plate):
        self.plate_result_label.setText(plate or "Không đọc được biển số")

    def worker_finished(self):
        self.capture_button.setEnabled(True)
        self.worker = None
        self.resources_changed.emit()

    def close_resources(self):
        self.stop_camera()
        if self.worker is not None:
            self.worker.wait()

    def is_processing(self):
        return self.worker is not None and self.worker.isRunning()


class MainWindow(QMainWindow):
    logout_requested = Signal()
    logout_cleanup_finished = Signal()
    window_closed = Signal()

    def __init__(self, database, role):
        super().__init__()
        if role not in (ADMIN_ROLE, EMPLOYEE_ROLE):
            raise ValueError(f"Vai trò không hợp lệ: {role}")
        self.database = database
        self.role = role
        self.is_admin = role == ADMIN_ROLE
        self._logout_preparing = False
        self._logout_cleanup_emitted = False
        self.setWindowTitle("Quản lý bãi giữ xe thông minh")
        self.resize(1200, 820)
        self.setMinimumSize(1000, 700)
        self._staff_original_id = None

        root = QWidget()
        root.setObjectName("dashboardRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 16, 22, 10)
        root_layout.setSpacing(10)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        eyebrow = QLabel("PARKING OPERATIONS")
        eyebrow.setObjectName("sectionEyebrow")
        title = QLabel("Trung tâm điều hành")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Giám sát phương tiện, dữ liệu và nhân sự")
        subtitle.setObjectName("pageSubtitle")
        title_block.addWidget(eyebrow)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch(1)

        self.role_label = QLabel(f"Đang đăng nhập: {role}")
        self.role_label.setStyleSheet(
            "background-color: #eef4ff; color: #245fcb; "
            "border: 1px solid #c7d7f5; border-radius: 12px; "
            "padding: 7px 12px; font-weight: 600;"
        )
        header.addWidget(self.role_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.model_status_label = QLabel("Đang khởi tạo model")
        self.model_status_label.setObjectName("modelStatus")
        self.model_status_label.setProperty("ready", "loading")
        self.model_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.model_status_label.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        header.addWidget(self.model_status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.logout_button = QPushButton("Đăng xuất")
        self.logout_button.setProperty("variant", "danger")
        self.logout_button.setToolTip("Kết thúc phiên hiện tại và đổi vai trò")
        self.logout_button.clicked.connect(self.request_logout)
        header.addWidget(self.logout_button, 0, Qt.AlignmentFlag.AlignVCenter)
        root_layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.addTab(self.create_operation_tab(), "Điều hành")
        if self.is_admin:
            self.tabs.addTab(self.create_logs_tab(), "Quản lý lịch sử")
            self.tabs.addTab(self.create_staff_tab(), "Quản lý nhân sự")
        self.tabs.addTab(self.create_review_tab(), "Đối chiếu lượt xe")
        root_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)
        self.tabs.currentChanged.connect(self.tab_changed)
        if self.is_admin:
            self.refresh_staff()
        self.statusBar().showMessage("Đang nạp và làm nóng model nhận diện...")
        self.model_warmup_worker = ModelWarmupWorker(self)
        self.model_warmup_worker.ready.connect(self.models_ready)
        self.model_warmup_worker.failed.connect(self.model_warmup_failed)
        self.model_warmup_worker.finished.connect(self.model_warmup_finished)
        self.model_warmup_worker.start()

    def model_warmup_finished(self):
        self.model_warmup_worker = None
        self._check_logout_cleanup()

    def models_ready(self):
        self.model_status_label.setText("Model nhận diện sẵn sàng")
        self.model_status_label.setProperty("ready", "true")
        self.model_status_label.style().unpolish(self.model_status_label)
        self.model_status_label.style().polish(self.model_status_label)
        self.statusBar().showMessage("Model nhận diện đã sẵn sàng.", 5000)

    def model_warmup_failed(self, message):
        self.model_status_label.setText("Model chưa sẵn sàng")
        self.model_status_label.setProperty("ready", "false")
        self.model_status_label.style().unpolish(self.model_status_label)
        self.model_status_label.style().polish(self.model_status_label)
        self.statusBar().showMessage("Không thể khởi tạo model nhận diện.")
        QMessageBox.warning(self, "Lỗi khởi tạo model", message)

    def create_operation_tab(self):
        tab = QWidget()
        tab.setObjectName("tabPage")
        layout = QGridLayout(tab)
        layout.setContentsMargins(4, 14, 4, 4)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(12)
        self.entry_panel = GatePanel("Vào", "0", self.database)
        self.exit_panel = GatePanel("Ra", "1", self.database)
        self.entry_panel.resources_changed.connect(self._check_logout_cleanup)
        self.exit_panel.resources_changed.connect(self._check_logout_cleanup)
        layout.addWidget(self.entry_panel, 0, 0)
        layout.addWidget(self.exit_panel, 0, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        self.entry_panel.record_saved.connect(self.refresh_after_record)
        self.exit_panel.record_saved.connect(self.refresh_after_record)
        return tab

    def refresh_after_record(self):
        if self.is_admin:
            self.refresh_logs()
        self.refresh_review()

    def request_logout(self):
        if self.entry_panel.is_processing() or self.exit_panel.is_processing():
            QMessageBox.warning(
                self,
                "Đang xử lý lượt xe",
                "Vui lòng đợi thao tác nhận diện và ghi dữ liệu hoàn tất "
                "trước khi đăng xuất.",
            )
            return
        self.logout_requested.emit()

    def prepare_for_logout(self):
        if self._logout_preparing:
            return
        self._logout_preparing = True
        self.setEnabled(False)
        self.entry_panel.request_camera_stop()
        self.exit_panel.request_camera_stop()
        self._check_logout_cleanup()

    def resources_stopped(self):
        return (
            self.entry_panel.camera is None
            and not self.entry_panel.is_processing()
            and self.exit_panel.camera is None
            and not self.exit_panel.is_processing()
            and (
                self.model_warmup_worker is None
                or not self.model_warmup_worker.isRunning()
            )
        )

    def _check_logout_cleanup(self):
        if (
            self._logout_preparing
            and not self._logout_cleanup_emitted
            and self.resources_stopped()
        ):
            self._logout_cleanup_emitted = True
            self.logout_cleanup_finished.emit()

    def _require_admin(self):
        if self.is_admin:
            return True
        QMessageBox.warning(
            self,
            "Không đủ quyền",
            "Chức năng này chỉ dành cho Admin.",
        )
        return False

    @staticmethod
    def setup_table(table):
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def create_logs_tab(self):
        tab = QWidget()
        tab.setObjectName("tabPage")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 14, 4, 4)
        layout.setSpacing(12)
        self.logs_table = QTableWidget()
        self.setup_table(self.logs_table)
        layout.addWidget(self.logs_table)

        buttons = QHBoxLayout()
        buttons.addStretch()
        refresh_button = QPushButton("Làm mới")
        export_button = QPushButton("Xuất báo cáo")
        export_button.setProperty("variant", "primary")
        buttons.addWidget(refresh_button)
        buttons.addWidget(export_button)
        layout.addLayout(buttons)
        refresh_button.clicked.connect(self.refresh_logs)
        export_button.clicked.connect(self.export_logs)
        return tab

    def create_staff_tab(self):
        tab = QWidget()
        tab.setObjectName("tabPage")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 14, 4, 4)
        layout.setSpacing(12)
        self.staff_table = QTableWidget()
        self.setup_table(self.staff_table)
        self.staff_table.itemSelectionChanged.connect(self.load_selected_staff)
        layout.addWidget(self.staff_table)

        form_box = QGroupBox("Thông tin nhân sự")
        form = QFormLayout(form_box)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        self.employee_id_input = QLineEdit()
        self.employee_name_input = QLineEdit()
        self.plate_input = QLineEdit()
        form.addRow("Mã nhân viên:", self.employee_id_input)
        form.addRow("Tên nhân viên:", self.employee_name_input)
        form.addRow("Biển số xe:", self.plate_input)
        layout.addWidget(form_box)

        buttons = QHBoxLayout()
        self.add_staff_button = QPushButton("Thêm mới")
        self.update_staff_button = QPushButton("Sửa")
        self.delete_staff_button = QPushButton("Xóa")
        self.add_staff_button.setProperty("variant", "primary")
        self.delete_staff_button.setProperty("variant", "danger")
        clear_button = QPushButton("Xóa trắng")
        for button in (
            self.add_staff_button,
            self.update_staff_button,
            self.delete_staff_button,
            clear_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.add_staff_button.clicked.connect(self.add_staff)
        self.update_staff_button.clicked.connect(self.update_staff)
        self.delete_staff_button.clicked.connect(self.delete_staff)
        clear_button.clicked.connect(self.clear_staff_form)
        self.update_staff_button.setEnabled(False)
        self.delete_staff_button.setEnabled(False)
        return tab

    def create_review_tab(self):
        tab = QWidget()
        tab.setObjectName("tabPage")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 14, 4, 4)
        layout.setSpacing(12)
        tables = QHBoxLayout()

        pending_box = QGroupBox("Lượt cần xác minh")
        pending_layout = QVBoxLayout(pending_box)
        self.pending_table = QTableWidget()
        self.setup_table(self.pending_table)
        self.pending_table.setMaximumHeight(190)
        self.pending_table.itemSelectionChanged.connect(
            self.load_pending_preview
        )
        pending_layout.addWidget(self.pending_table)
        tables.addWidget(pending_box, 1)

        sessions_box = QGroupBox("Các lượt vào đang mở")
        sessions_layout = QVBoxLayout(sessions_box)
        self.open_sessions_table = QTableWidget()
        self.setup_table(self.open_sessions_table)
        self.open_sessions_table.setMaximumHeight(190)
        self.open_sessions_table.itemSelectionChanged.connect(
            self.load_session_preview
        )
        sessions_layout.addWidget(self.open_sessions_table)
        tables.addWidget(sessions_box, 1)
        layout.addLayout(tables)

        previews = QHBoxLayout()
        self.pending_preview_labels = self.create_review_previews(
            "Ảnh lượt đang xử lý"
        )
        self.session_preview_labels = self.create_review_previews(
            "Ảnh lượt vào được chọn"
        )
        previews.addWidget(self.pending_preview_labels[0], 1)
        previews.addWidget(self.session_preview_labels[0], 1)
        layout.addLayout(previews, 1)

        form = QHBoxLayout()
        self.review_plate_input = QLineEdit()
        self.review_plate_input.setPlaceholderText(
            "Biển số xác nhận hoặc sửa lại"
        )
        self.review_button = QPushButton("Xác nhận đối chiếu")
        self.review_button.setProperty("variant", "primary")
        refresh_button = QPushButton("Làm mới")
        form.addWidget(QLabel("Biển số:"))
        form.addWidget(self.review_plate_input, 1)
        form.addWidget(self.review_button)
        form.addWidget(refresh_button)
        layout.addLayout(form)
        self.review_button.clicked.connect(self.resolve_selected_log)
        refresh_button.clicked.connect(self.refresh_review)
        self.refresh_review()
        return tab

    @staticmethod
    def create_review_previews(title):
        box = QGroupBox(title)
        layout = QHBoxLayout(box)
        labels = []
        for caption in ("Toàn cảnh", "Biển số", "Xe"):
            column = QVBoxLayout()
            column.addWidget(QLabel(caption))
            image_label = QLabel("Chưa có ảnh")
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setMinimumSize(100, 100)
            image_label.setStyleSheet(
                "background-color: #f1f4f8; color: #748198; "
                "border: 1px solid #dfe5ed; border-radius: 6px;"
            )
            column.addWidget(image_label, 1)
            layout.addLayout(column, 1)
            labels.append(image_label)
        return box, labels

    def show_frame_data(self, table, frame):
        table.clear()
        table.setColumnCount(len(frame.columns))
        table.setRowCount(len(frame.index))
        table.setHorizontalHeaderLabels(list(frame.columns))
        for row_index, row in enumerate(frame.itertuples(index=False, name=None)):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, column_index, item)
        hidden_columns = {
            "Mã lượt",
            "Mã phiên",
            "Ảnh toàn cảnh",
            "Ảnh biển số",
            "Ảnh xe",
            "Lỗi nhận diện",
        }
        for column_index, column in enumerate(frame.columns):
            table.setColumnHidden(column_index, column in hidden_columns)

    def refresh_logs(self):
        if not self._require_admin():
            return
        try:
            self.show_frame_data(self.logs_table, self.database.read_logs())
        except ExcelDatabaseError as error:
            QMessageBox.warning(self, "Không thể tải lịch sử", str(error))

    def refresh_review(self):
        try:
            pending = self.database.get_pending_logs()
            sessions = self.database.get_open_sessions()
        except ExcelDatabaseError as error:
            QMessageBox.warning(self, "Không thể tải lượt đối chiếu", str(error))
            return

        self._pending_rows = pending.to_dict("records")
        self._open_session_rows = sessions.to_dict("records")
        self._populate_review_table(
            self.pending_table,
            self._pending_rows,
            [
                "Thời gian",
                "Cổng",
                "Biển số OCR",
                "Trạng thái",
                "Lỗi nhận diện",
            ],
            "Mã lượt",
        )
        self._populate_review_table(
            self.open_sessions_table,
            self._open_session_rows,
            ["Thời gian", "Biển số", "Loại xe", "Mã nhân viên"],
            "Mã phiên",
        )
        self.clear_review_previews()

    @staticmethod
    def _populate_review_table(table, rows, columns, id_column):
        table.clear()
        table.setColumnCount(len(columns) + 1)
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels([id_column, *columns])
        table.setColumnHidden(0, True)
        for row_index, row in enumerate(rows):
            id_item = QTableWidgetItem(str(row.get(id_column, "")))
            id_item.setData(Qt.ItemDataRole.UserRole, row)
            table.setItem(row_index, 0, id_item)
            for column_index, column in enumerate(columns, start=1):
                item = QTableWidgetItem(str(row.get(column, "")))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, column_index, item)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

    def load_pending_preview(self):
        row_index = self.pending_table.currentRow()
        if not 0 <= row_index < len(self._pending_rows):
            self.clear_review_previews()
            return
        pending = self._pending_rows[row_index]
        self.open_sessions_table.clearSelection()
        self.clear_image_labels(self.session_preview_labels[1])
        self.show_saved_images(
            self.pending_preview_labels[1],
            pending,
        )
        self.review_plate_input.setText(
            pending.get("Biển số OCR", "") or pending.get("Biển số", "")
        )
        if pending.get("Cổng") == "Ra":
            for index, session in enumerate(self._open_session_rows):
                if (
                    pending.get("Biển số OCR")
                    and normalize_plate(session.get("Biển số", ""))
                    == normalize_plate(pending["Biển số OCR"])
                ):
                    self.open_sessions_table.selectRow(index)
                    break

    def load_session_preview(self):
        row_index = self.open_sessions_table.currentRow()
        if not 0 <= row_index < len(self._open_session_rows):
            self.clear_image_labels(self.session_preview_labels[1])
            return
        session = self._open_session_rows[row_index]
        self.show_saved_images(self.session_preview_labels[1], session)
        pending_index = self.pending_table.currentRow()
        if (
            0 <= pending_index < len(self._pending_rows)
            and self._pending_rows[pending_index].get("Cổng") == "Ra"
        ):
            self.review_plate_input.setText(session.get("Biển số", ""))

    def show_saved_images(self, labels, record):
        columns = ("Ảnh toàn cảnh", "Ảnh biển số", "Ảnh xe")
        for label, column in zip(labels, columns):
            relative_path = record.get(column, "")
            if not relative_path:
                label.clear()
                label.setText("Không có ảnh")
                continue
            capture_directory = (
                self.database.directory / "captures"
            ).resolve()
            image_path = (
                self.database.directory / Path(relative_path)
            ).resolve()
            try:
                image_path.relative_to(capture_directory)
            except ValueError:
                label.clear()
                label.setText("Đường dẫn ảnh không hợp lệ")
                continue
            try:
                image = cv2.imread(str(image_path))
            except cv2.error:
                image = None
            if image is None:
                label.clear()
                label.setText("Không thể đọc ảnh")
                continue
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb_image.shape
            qimage = QImage(
                rgb_image.data,
                width,
                height,
                channels * width,
                QImage.Format.Format_RGB888,
            ).copy()
            label.setPixmap(
                QPixmap.fromImage(qimage).scaled(
                    label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    @staticmethod
    def clear_image_labels(labels):
        for label in labels:
            label.clear()
            label.setText("Chưa có ảnh")

    def clear_review_previews(self):
        self.clear_image_labels(self.pending_preview_labels[1])
        self.clear_image_labels(self.session_preview_labels[1])
        self.review_plate_input.clear()

    def resolve_selected_log(self):
        pending_index = self.pending_table.currentRow()
        if not 0 <= pending_index < len(self._pending_rows):
            QMessageBox.warning(
                self,
                "Chưa chọn lượt",
                "Vui lòng chọn lượt cần xác minh hoặc đối chiếu.",
            )
            return

        pending = self._pending_rows[pending_index]
        session_id = ""
        if pending.get("Cổng") == "Ra":
            session_index = self.open_sessions_table.currentRow()
            if not 0 <= session_index < len(self._open_session_rows):
                QMessageBox.warning(
                    self,
                    "Chưa chọn lượt vào",
                    "Vui lòng chọn lượt vào cần ghép với xe ra.",
                )
                return
            session_id = self._open_session_rows[session_index]["Mã phiên"]

        try:
            self.database.resolve_pending_log(
                pending["Mã lượt"],
                self.review_plate_input.text(),
                session_id,
            )
        except (ExcelDatabaseError, ValueError) as error:
            QMessageBox.warning(self, "Không thể đối chiếu lượt xe", str(error))
            return

        self.refresh_review()
        if self.is_admin:
            self.refresh_logs()
        QMessageBox.information(
            self,
            "Đối chiếu lượt xe",
            "Đã xác nhận thông tin và cập nhật phiên gửi xe.",
        )

    def refresh_staff(self):
        if not self._require_admin():
            return
        try:
            self.show_frame_data(self.staff_table, self.database.read_staff())
        except ExcelDatabaseError as error:
            QMessageBox.warning(self, "Không thể tải nhân sự", str(error))

    def tab_changed(self, index):
        if self.tabs.tabText(index) == "Quản lý lịch sử":
            self.refresh_logs()
        elif self.tabs.tabText(index) == "Quản lý nhân sự":
            self.refresh_staff()
        elif self.tabs.tabText(index) == "Đối chiếu lượt xe":
            self.refresh_review()

    def export_logs(self):
        if not self._require_admin():
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Xuất báo cáo lịch sử",
            "bao_cao_bai_giu_xe.xlsx",
            "Tệp Excel (*.xlsx);;Tệp CSV (*.csv)",
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".csv" if "CSV" in selected_filter else ".xlsx"
        try:
            frame = self.database.read_logs()
            if Path(path).suffix.lower() == ".csv":
                frame.to_csv(path, index=False, encoding="utf-8-sig")
            else:
                frame.to_excel(path, index=False, engine="openpyxl")
        except PermissionError:
            QMessageBox.warning(
                self,
                "Không thể xuất báo cáo",
                "Tệp đang được mở hoặc bị khóa. Vui lòng đóng tệp trong Microsoft Excel rồi thử lại.",
            )
        except (ExcelDatabaseError, OSError, ValueError, ImportError) as error:
            QMessageBox.warning(self, "Không thể xuất báo cáo", str(error))
        else:
            QMessageBox.information(self, "Xuất báo cáo", "Đã xuất báo cáo thành công.")

    def load_selected_staff(self):
        if not self._require_admin():
            return
        selected = self.staff_table.selectedItems()
        has_selection = bool(selected)
        self.update_staff_button.setEnabled(has_selection)
        self.delete_staff_button.setEnabled(has_selection)
        if not has_selection:
            return
        row = self.staff_table.currentRow()
        values = [
            self.staff_table.item(row, column).text()
            for column in range(self.staff_table.columnCount())
        ]
        self._staff_original_id = values[0]
        self.employee_id_input.setText(values[0])
        self.employee_name_input.setText(values[1])
        self.plate_input.setText(values[2])

    def staff_form_values(self):
        return {
            "Mã nhân viên": self.employee_id_input.text(),
            "Tên nhân viên": self.employee_name_input.text(),
            "Biển số xe": self.plate_input.text(),
        }

    def add_staff(self):
        if not self._require_admin():
            return
        try:
            self.database.add_staff(self.staff_form_values())
        except (ExcelDatabaseError, ValueError) as error:
            QMessageBox.warning(self, "Không thể thêm nhân sự", str(error))
            return
        self.refresh_staff()
        self.clear_staff_form()
        QMessageBox.information(self, "Quản lý nhân sự", "Đã thêm nhân sự thành công.")

    def update_staff(self):
        if not self._require_admin():
            return
        if self._staff_original_id is None:
            QMessageBox.warning(self, "Chưa chọn nhân sự", "Vui lòng chọn nhân sự cần sửa.")
            return
        try:
            self.database.update_staff(self._staff_original_id, self.staff_form_values())
        except (ExcelDatabaseError, ValueError) as error:
            QMessageBox.warning(self, "Không thể sửa nhân sự", str(error))
            return
        self.refresh_staff()
        self.clear_staff_form()
        QMessageBox.information(self, "Quản lý nhân sự", "Đã cập nhật nhân sự thành công.")

    def delete_staff(self):
        if not self._require_admin():
            return
        if self._staff_original_id is None:
            QMessageBox.warning(self, "Chưa chọn nhân sự", "Vui lòng chọn nhân sự cần xóa.")
            return
        answer = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f'Bạn có chắc chắn muốn xóa nhân viên “{self._staff_original_id}”?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.delete_staff(self._staff_original_id)
        except (ExcelDatabaseError, ValueError) as error:
            QMessageBox.warning(self, "Không thể xóa nhân sự", str(error))
            return
        self.refresh_staff()
        self.clear_staff_form()
        QMessageBox.information(self, "Quản lý nhân sự", "Đã xóa nhân sự thành công.")

    def clear_staff_form(self):
        if not self._require_admin():
            return
        self.staff_table.clearSelection()
        self._staff_original_id = None
        self.employee_id_input.clear()
        self.employee_name_input.clear()
        self.plate_input.clear()
        self.update_staff_button.setEnabled(False)
        self.delete_staff_button.setEnabled(False)

    def closeEvent(self, event):
        if not self._logout_preparing:
            self.entry_panel.close_resources()
            self.exit_panel.close_resources()
            if (
                self.model_warmup_worker is not None
                and self.model_warmup_worker.isRunning()
            ):
                self.model_warmup_worker.wait()
            self.window_closed.emit()
        event.accept()

from datetime import datetime
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from anpr import ANPRError, recognize_plate
from camera_thread import CameraThread
from excel_db import ExcelDatabase, ExcelDatabaseError


class RecognitionWorker(QThread):
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, image, gate, database, parent=None):
        super().__init__(parent)
        self.image = image
        self.gate = gate
        self.database = database

    def run(self):
        try:
            plate = recognize_plate(self.image)
            staff = self.database.find_staff_by_plate(plate)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = {
                "Thời gian": timestamp,
                "Biển số": plate,
                "Cổng": self.gate,
                "Loại xe": "Nhân viên" if staff else "Khách vãng lai",
                "Mã nhân viên": staff["Mã nhân viên"] if staff else "",
                "Tên nhân viên": staff["Tên nhân viên"] if staff else "",
            }
            self.database.add_log(result)
        except (ANPRError, ExcelDatabaseError, ValueError) as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(f"Đã xảy ra lỗi khi ghi nhận lượt xe: {error}")
        else:
            self.completed.emit(result)


class GatePanel(QGroupBox):
    def __init__(self, gate, default_source, database, parent=None):
        super().__init__(f"Lối {gate}", parent)
        self.gate = gate
        self.database = database
        self.camera = None
        self.worker = None

        layout = QVBoxLayout(self)
        source_row = QHBoxLayout()
        self.source_input = QLineEdit(default_source)
        self.source_input.setPlaceholderText("Nhập chỉ số webcam hoặc đường dẫn tệp video")
        self.browse_button = QPushButton("Chọn tệp video...")
        self.open_button = QPushButton("Mở nguồn")
        source_row.addWidget(QLabel("Nguồn hình ảnh:"))
        source_row.addWidget(self.source_input, 1)
        source_row.addWidget(self.browse_button)
        source_row.addWidget(self.open_button)
        layout.addLayout(source_row)

        self.video_label = QLabel("Chưa mở nguồn hình ảnh")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(480, 270)
        self.video_label.setStyleSheet("background-color: #20252b; color: white;")
        layout.addWidget(self.video_label, 1)

        self.result_label = QLabel("Chưa ghi nhận lượt xe")
        self.result_label.setWordWrap(True)
        self.capture_button = QPushButton(f"Chụp & Ghi nhận Xe {gate}")
        self.capture_button.setMinimumHeight(38)
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

    def show_frame(self, image):
        pixmap = QPixmap.fromImage(image).scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
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
        image = self.camera.lay_khung_hinh()
        if image is None:
            QMessageBox.warning(self, "Chưa có hình ảnh", "Nguồn hình ảnh chưa cung cấp được khung hình.")
            return
        if self.worker is not None and self.worker.isRunning():
            return

        self.capture_button.setEnabled(False)
        self.result_label.setText("Đang nhận diện biển số và ghi dữ liệu...")
        self.worker = RecognitionWorker(image, self.gate, self.database, self)
        self.worker.completed.connect(self.show_result)
        self.worker.failed.connect(self.show_record_error)
        self.worker.finished.connect(self.worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def show_result(self, result):
        employee = result["Mã nhân viên"]
        if employee:
            detail = f'Nhân viên {employee} - {result["Tên nhân viên"]}'
        else:
            detail = "Khách vãng lai"
        self.result_label.setText(
            f'Đã ghi nhận xe {result["Biển số"]} tại lối {self.gate}. {detail}.'
        )

    def show_record_error(self, message):
        self.result_label.setText("Không thể ghi nhận lượt xe.")
        QMessageBox.warning(self, "Không thể ghi nhận", message)

    def worker_finished(self):
        self.capture_button.setEnabled(True)
        self.worker = None

    def close_resources(self):
        self.stop_camera()
        if self.worker is not None:
            self.worker.wait()


class MainWindow(QMainWindow):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.setWindowTitle("Quản lý bãi giữ xe thông minh")
        self.resize(1200, 820)
        self._staff_original_id = None

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self.create_operation_tab(), "Điều hành")
        self.tabs.addTab(self.create_logs_tab(), "Quản lý lịch sử")
        self.tabs.addTab(self.create_staff_tab(), "Quản lý nhân sự")
        self.tabs.currentChanged.connect(self.tab_changed)
        self.refresh_staff()

    def create_operation_tab(self):
        tab = QWidget()
        layout = QGridLayout(tab)
        self.entry_panel = GatePanel("Vào", "0", self.database)
        self.exit_panel = GatePanel("Ra", "1", self.database)
        layout.addWidget(self.entry_panel, 0, 0)
        layout.addWidget(self.exit_panel, 0, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        return tab

    @staticmethod
    def setup_table(table):
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def create_logs_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.logs_table = QTableWidget()
        self.setup_table(self.logs_table)
        layout.addWidget(self.logs_table)

        buttons = QHBoxLayout()
        buttons.addStretch()
        refresh_button = QPushButton("Làm mới")
        export_button = QPushButton("Xuất báo cáo")
        buttons.addWidget(refresh_button)
        buttons.addWidget(export_button)
        layout.addLayout(buttons)
        refresh_button.clicked.connect(self.refresh_logs)
        export_button.clicked.connect(self.export_logs)
        return tab

    def create_staff_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.staff_table = QTableWidget()
        self.setup_table(self.staff_table)
        self.staff_table.itemSelectionChanged.connect(self.load_selected_staff)
        layout.addWidget(self.staff_table)

        form_box = QGroupBox("Thông tin nhân sự")
        form = QFormLayout(form_box)
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

    def refresh_logs(self):
        try:
            self.show_frame_data(self.logs_table, self.database.read_logs())
        except ExcelDatabaseError as error:
            QMessageBox.warning(self, "Không thể tải lịch sử", str(error))

    def refresh_staff(self):
        try:
            self.show_frame_data(self.staff_table, self.database.read_staff())
        except ExcelDatabaseError as error:
            QMessageBox.warning(self, "Không thể tải nhân sự", str(error))

    def tab_changed(self, index):
        if self.tabs.tabText(index) == "Quản lý lịch sử":
            self.refresh_logs()
        elif self.tabs.tabText(index) == "Quản lý nhân sự":
            self.refresh_staff()

    def export_logs(self):
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
        try:
            self.database.add_staff(self.staff_form_values())
        except (ExcelDatabaseError, ValueError) as error:
            QMessageBox.warning(self, "Không thể thêm nhân sự", str(error))
            return
        self.refresh_staff()
        self.clear_staff_form()
        QMessageBox.information(self, "Quản lý nhân sự", "Đã thêm nhân sự thành công.")

    def update_staff(self):
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
        self.staff_table.clearSelection()
        self._staff_original_id = None
        self.employee_id_input.clear()
        self.employee_name_input.clear()
        self.plate_input.clear()
        self.update_staff_button.setEnabled(False)
        self.delete_staff_button.setEnabled(False)

    def closeEvent(self, event):
        self.entry_panel.close_resources()
        self.exit_panel.close_resources()
        event.accept()

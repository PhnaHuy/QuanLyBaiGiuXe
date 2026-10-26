import threading

import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class CameraThread(QThread):
    khung_hinh_moi = Signal(QImage)
    loi_nguon = Signal(str)
    ket_thuc_nguon = Signal()

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self._stop_event = threading.Event()
        self._frame_lock = threading.Lock()
        self._current_frame = None

    def lay_khung_hinh(self):
        with self._frame_lock:
            if self._current_frame is None:
                return None
            return self._current_frame.copy()

    def dung(self):
        self._stop_event.set()

    def run(self):
        capture = None
        try:
            capture = cv2.VideoCapture(self.source)
            if not capture.isOpened():
                self.loi_nguon.emit("Không thể mở nguồn hình ảnh. Hãy kiểm tra webcam hoặc đường dẫn video.")
                return

            while not self._stop_event.is_set():
                success, frame = capture.read()
                if not success:
                    if isinstance(self.source, str):
                        self.ket_thuc_nguon.emit()
                    else:
                        self.loi_nguon.emit("Không nhận được hình ảnh từ webcam. Hãy kiểm tra kết nối và quyền truy cập.")
                    break

                with self._frame_lock:
                    self._current_frame = frame.copy()

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channels = rgb_frame.shape
                image = QImage(
                    rgb_frame.data,
                    width,
                    height,
                    channels * width,
                    QImage.Format.Format_RGB888,
                ).copy()
                self.khung_hinh_moi.emit(image)
                self.msleep(20)
        except cv2.error as error:
            self.loi_nguon.emit(f"OpenCV không thể xử lý nguồn hình ảnh: {error}")
        except Exception as error:
            self.loi_nguon.emit(f"Đã xảy ra lỗi với nguồn hình ảnh: {error}")
        finally:
            if capture is not None:
                capture.release()

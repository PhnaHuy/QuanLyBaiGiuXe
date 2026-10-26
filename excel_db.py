from pathlib import Path
from threading import RLock

import pandas as pd

from anpr import normalize_plate


STAFF_COLUMNS = ["Mã nhân viên", "Tên nhân viên", "Biển số xe"]
LOG_COLUMNS = ["Thời gian", "Biển số", "Cổng", "Loại xe", "Mã nhân viên"]


class ExcelDatabaseError(Exception):
    pass


class ExcelDatabase:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.staff_path = self.directory / "staff.xlsx"
        self.logs_path = self.directory / "parking_logs.xlsx"
        self._lock = RLock()

    @staticmethod
    def _permission_message(path):
        return (
            f"Không thể ghi tệp “{path.name}” vì tệp đang được mở hoặc bị khóa. "
            "Vui lòng đóng tệp trong Microsoft Excel rồi thử lại."
        )

    def initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._initialize_file(self.staff_path, STAFF_COLUMNS)
            self._initialize_file(self.logs_path, LOG_COLUMNS)

    def _initialize_file(self, path, columns):
        if path.exists():
            return
        try:
            pd.DataFrame(columns=columns).to_excel(path, index=False, engine="openpyxl")
        except PermissionError as error:
            raise ExcelDatabaseError(self._permission_message(path)) from error

    def _read_frame(self, path, columns):
        try:
            frame = pd.read_excel(path, engine="openpyxl", dtype=str).fillna("")
        except PermissionError as error:
            raise ExcelDatabaseError(
                f"Không thể đọc tệp “{path.name}”. Vui lòng đóng tệp trong Microsoft Excel rồi thử lại."
            ) from error
        except (OSError, ValueError, ImportError) as error:
            raise ExcelDatabaseError(f"Không thể đọc tệp “{path.name}”: {error}") from error

        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ExcelDatabaseError(
                f"Tệp “{path.name}” thiếu cột bắt buộc: {', '.join(missing)}."
            )
        return frame.loc[:, columns].fillna("")

    def read_staff(self):
        with self._lock:
            return self._read_frame(self.staff_path, STAFF_COLUMNS)

    def read_logs(self):
        with self._lock:
            return self._read_frame(self.logs_path, LOG_COLUMNS)

    def _write_frame(self, frame, path):
        try:
            frame.to_excel(path, index=False, engine="openpyxl")
        except PermissionError as error:
            raise ExcelDatabaseError(self._permission_message(path)) from error
        except (OSError, ValueError, ImportError) as error:
            raise ExcelDatabaseError(f"Không thể ghi tệp “{path.name}”: {error}") from error

    @staticmethod
    def _validated_staff(values):
        staff = {column: str(values.get(column, "")).strip() for column in STAFF_COLUMNS}
        if not all(staff.values()):
            raise ValueError("Vui lòng nhập đầy đủ mã nhân viên, tên nhân viên và biển số xe.")
        return staff

    @staticmethod
    def _check_duplicates(frame, staff, ignored_id=None):
        others = frame[frame["Mã nhân viên"] != ignored_id]
        if (others["Mã nhân viên"].str.strip() == staff["Mã nhân viên"]).any():
            raise ValueError("Mã nhân viên này đã tồn tại.")
        new_plate = normalize_plate(staff["Biển số xe"])
        if any(normalize_plate(value) == new_plate for value in others["Biển số xe"]):
            raise ValueError("Biển số xe này đã được gán cho nhân viên khác.")

    def add_staff(self, values):
        staff = self._validated_staff(values)
        with self._lock:
            frame = self.read_staff()
            self._check_duplicates(frame, staff)
            self._write_frame(pd.concat([frame, pd.DataFrame([staff])], ignore_index=True), self.staff_path)

    def update_staff(self, original_id, values):
        staff = self._validated_staff(values)
        with self._lock:
            frame = self.read_staff()
            indices = frame.index[frame["Mã nhân viên"].str.strip() == original_id]
            if len(indices) != 1:
                raise ValueError("Không tìm thấy duy nhất nhân viên cần sửa. Vui lòng làm mới danh sách.")
            self._check_duplicates(frame, staff, ignored_id=original_id)
            for column, value in staff.items():
                frame.loc[indices[0], column] = value
            self._write_frame(frame, self.staff_path)

    def delete_staff(self, employee_id):
        with self._lock:
            frame = self.read_staff()
            remaining = frame[frame["Mã nhân viên"].str.strip() != employee_id]
            if len(remaining) == len(frame):
                raise ValueError("Không tìm thấy nhân viên cần xóa. Vui lòng làm mới danh sách.")
            self._write_frame(remaining, self.staff_path)

    def find_staff_by_plate(self, plate):
        target = normalize_plate(plate)
        if not target:
            return None
        frame = self.read_staff()
        matches = frame[frame["Biển số xe"].map(normalize_plate) == target]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    def add_log(self, values):
        log = {column: str(values.get(column, "")).strip() for column in LOG_COLUMNS}
        with self._lock:
            frame = self.read_logs()
            self._write_frame(pd.concat([frame, pd.DataFrame([log])], ignore_index=True), self.logs_path)

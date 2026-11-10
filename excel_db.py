from io import BytesIO
import os
from pathlib import Path
import tempfile
from threading import RLock

import msoffcrypto
import pandas as pd
from msoffcrypto.exceptions import (
    DecryptionError,
    EncryptionError,
    FileFormatError,
    InvalidKeyError,
    ParseError,
)

from auth import ADMIN_DEFAULT_PASSWORD
from anpr import normalize_plate


STAFF_COLUMNS = ["Mã nhân viên", "Tên nhân viên", "Biển số xe"]
STATUS_AUTO_MATCHED = "Đã đối chiếu tự động"
STATUS_PENDING_RECONCILIATION = "Chờ đối chiếu"
STATUS_ENTRY_PENDING_VERIFICATION = "Đang gửi - chờ xác minh"
LOG_COLUMNS = [
    "Thời gian",
    "Biển số",
    "Cổng",
    "Loại xe",
    "Mã nhân viên",
    "Mã lượt",
    "Mã phiên",
    "Trạng thái",
    "Biển số OCR",
    "Ảnh toàn cảnh",
    "Ảnh biển số",
    "Ảnh xe",
    "Lỗi nhận diện",
]


class ExcelDatabaseError(Exception):
    pass


class ExcelDatabase:
    def __init__(self, directory, staff_password=ADMIN_DEFAULT_PASSWORD):
        self.directory = Path(directory)
        self.staff_path = self.directory / "staff.xlsx"
        self.logs_path = self.directory / "parking_logs.xlsx"
        self.staff_password = staff_password
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
            self._initialize_staff_file()
            self._initialize_file(self.logs_path, LOG_COLUMNS)
            self._migrate_pending_entry_sessions()

    def _migrate_pending_entry_sessions(self):
        frame = self.read_logs()
        pending_entries = (
            (frame["Cổng"] == "Vào")
            & (frame["Trạng thái"] == "Chờ xác minh")
            & (frame["Mã phiên"].str.strip() == "")
            & (frame["Mã lượt"].str.strip() != "")
        )
        if not pending_entries.any():
            return

        frame.loc[pending_entries, "Mã phiên"] = frame.loc[
            pending_entries, "Mã lượt"
        ]
        frame.loc[pending_entries, "Trạng thái"] = (
            STATUS_ENTRY_PENDING_VERIFICATION
        )
        self._write_frame(frame.loc[:, LOG_COLUMNS], self.logs_path)

    def _initialize_staff_file(self):
        if self.staff_path.exists():
            try:
                payload = self.staff_path.read_bytes()
            except PermissionError as error:
                raise ExcelDatabaseError(
                    f"Không thể đọc tệp “{self.staff_path.name}”. "
                    "Vui lòng đóng tệp trong Microsoft Excel rồi thử lại."
                ) from error
            except OSError as error:
                raise ExcelDatabaseError(
                    f"Không thể đọc tệp “{self.staff_path.name}”: {error}"
                ) from error
            decrypted, is_encrypted = self._decrypt_staff_workbook(payload)
            self._read_frame_from_source(
                BytesIO(decrypted),
                self.staff_path,
                STAFF_COLUMNS,
            )
            if not is_encrypted:
                self._write_encrypted_staff_bytes(payload)
            return

        buffer = BytesIO()
        pd.DataFrame(columns=STAFF_COLUMNS).to_excel(
            buffer,
            index=False,
            engine="openpyxl",
        )
        self._write_encrypted_staff_bytes(buffer.getvalue())

    def _initialize_file(self, path, columns):
        if path.exists():
            return
        try:
            pd.DataFrame(columns=columns).to_excel(path, index=False, engine="openpyxl")
        except PermissionError as error:
            raise ExcelDatabaseError(self._permission_message(path)) from error

    def _read_frame_from_source(self, source, path, columns):
        try:
            frame = pd.read_excel(
                source,
                engine="openpyxl",
                dtype=str,
            ).fillna("")
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
        return frame.fillna("")

    def _read_frame(self, path, columns):
        if path == self.staff_path:
            try:
                payload = path.read_bytes()
            except PermissionError as error:
                raise ExcelDatabaseError(
                    f"Không thể đọc tệp “{path.name}”. "
                    "Vui lòng đóng tệp trong Microsoft Excel rồi thử lại."
                ) from error
            except OSError as error:
                raise ExcelDatabaseError(
                    f"Không thể đọc tệp “{path.name}”: {error}"
                ) from error
            decrypted, _is_encrypted = self._decrypt_staff_workbook(payload)
            source = BytesIO(decrypted)
        else:
            source = path
        return self._read_frame_from_source(source, path, columns)

    def _decrypt_staff_workbook(self, payload):
        try:
            office_file = msoffcrypto.OfficeFile(BytesIO(payload))
            if not office_file.is_encrypted():
                return payload, False
            office_file.load_key(
                password=self.staff_password,
                verify_password=True,
            )
            decrypted = BytesIO()
            office_file.decrypt(decrypted, verify_integrity=True)
        except InvalidKeyError as error:
            raise ExcelDatabaseError(
                "Không thể mở staff.xlsx: mật khẩu không khớp hoặc tệp đã bị thay đổi."
            ) from error
        except (DecryptionError, FileFormatError, ParseError) as error:
            raise ExcelDatabaseError(
                f"Không thể giải mã staff.xlsx: {error}"
            ) from error
        return decrypted.getvalue(), True

    def _write_encrypted_staff_bytes(self, payload):
        try:
            office_file = msoffcrypto.OfficeFile(BytesIO(payload))
            encrypted = BytesIO()
            office_file.encrypt(self.staff_password, encrypted)
            self._atomic_write(self.staff_path, encrypted.getvalue())
        except PermissionError as error:
            raise ExcelDatabaseError(
                self._permission_message(self.staff_path)
            ) from error
        except (EncryptionError, FileFormatError, ParseError, OSError) as error:
            raise ExcelDatabaseError(
                f"Không thể mã hóa tệp “{self.staff_path.name}”: {error}"
            ) from error

    @staticmethod
    def _atomic_write(path, payload):
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def read_staff(self):
        with self._lock:
            return self._read_frame(self.staff_path, STAFF_COLUMNS).loc[
                :, STAFF_COLUMNS
            ]

    def read_logs(self):
        with self._lock:
            frame = self._read_frame(self.logs_path, LOG_COLUMNS[:5])
            for column in LOG_COLUMNS[5:]:
                if column not in frame.columns:
                    frame[column] = ""
            return frame.loc[:, LOG_COLUMNS].fillna("")

    def _write_frame(self, frame, path):
        try:
            if path == self.staff_path:
                buffer = BytesIO()
                frame.to_excel(buffer, index=False, engine="openpyxl")
                self._write_encrypted_staff_bytes(buffer.getvalue())
            else:
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
            if log["Cổng"] == "Vào":
                log["Mã phiên"] = log["Mã lượt"]
                if log["Trạng thái"] == "Chờ xác minh":
                    log["Trạng thái"] = STATUS_ENTRY_PENDING_VERIFICATION
                elif not log["Trạng thái"]:
                    log["Trạng thái"] = "Đang gửi"
            elif log["Cổng"] == "Ra":
                log = self._match_exit_to_open_session(frame, log)
            frame = pd.concat([frame, pd.DataFrame([log])], ignore_index=True)
            self._write_frame(frame.loc[:, LOG_COLUMNS], self.logs_path)
            return log

    def _match_exit_to_open_session(self, logs, exit_log):
        plate = normalize_plate(
            exit_log.get("Biển số OCR") or exit_log.get("Biển số", "")
        )
        if not plate:
            return exit_log

        open_sessions = self._open_sessions_from_logs(logs)
        matches = open_sessions[
            open_sessions["Biển số"].map(normalize_plate) == plate
        ]
        if len(matches) != 1:
            return exit_log

        entry = matches.iloc[0]
        entry_rows = logs.index[logs["Mã lượt"] == entry["Mã lượt"]]
        if len(entry_rows) != 1 or not entry["Mã phiên"]:
            return exit_log

        exit_log["Biển số"] = entry["Biển số"]
        exit_log["Mã nhân viên"] = entry["Mã nhân viên"]
        exit_log["Loại xe"] = entry["Loại xe"]
        exit_log["Mã phiên"] = entry["Mã phiên"]
        exit_log["Trạng thái"] = STATUS_AUTO_MATCHED
        logs.loc[entry_rows[0], "Trạng thái"] = "Đã ra"
        return exit_log

    @staticmethod
    def _open_sessions_from_logs(logs):
        entries = logs[
            (logs["Cổng"] == "Vào")
            & (logs["Mã phiên"].str.strip() != "")
        ].copy()
        exited_sessions = set(
            logs.loc[logs["Cổng"] == "Ra", "Mã phiên"].str.strip()
        )
        open_sessions = entries[
            ~entries["Mã phiên"].isin(exited_sessions)
        ]
        return open_sessions.sort_values(
            "Thời gian",
            ascending=False,
            kind="stable",
        ).reset_index(drop=True)

    def get_pending_logs(self):
        with self._lock:
            frame = self.read_logs()
            return frame[
                frame["Trạng thái"].isin(
                    [
                        "Chờ xác minh",
                        STATUS_ENTRY_PENDING_VERIFICATION,
                        STATUS_PENDING_RECONCILIATION,
                    ]
                )
            ].copy()

    def get_open_sessions(self):
        with self._lock:
            return self._open_sessions_from_logs(self.read_logs())

    def resolve_pending_log(self, event_id, plate, session_id=""):
        normalized_plate = normalize_plate(plate)
        if not normalized_plate:
            raise ValueError("Vui lòng nhập hoặc chọn biển số hợp lệ.")

        with self._lock:
            frame = self.read_logs()
            matches = frame.index[frame["Mã lượt"] == event_id]
            if len(matches) != 1:
                raise ValueError("Không tìm thấy duy nhất lượt cần đối chiếu. Hãy làm mới danh sách.")
            index = matches[0]
            row = frame.loc[index]
            if row["Trạng thái"] not in (
                "Chờ xác minh",
                STATUS_ENTRY_PENDING_VERIFICATION,
                STATUS_PENDING_RECONCILIATION,
            ):
                raise ValueError("Lượt này đã được đối chiếu hoặc không còn chờ xử lý.")

            if row["Cổng"] == "Vào":
                staff = self.find_staff_by_plate(normalized_plate)
                frame.loc[index, "Biển số"] = normalized_plate
                frame.loc[index, "Mã nhân viên"] = (
                    staff["Mã nhân viên"] if staff else ""
                )
                frame.loc[index, "Loại xe"] = (
                    "Nhân viên" if staff else "Khách vãng lai"
                )
                frame.loc[index, "Mã phiên"] = event_id
                frame.loc[index, "Trạng thái"] = "Đang gửi"
            elif row["Cổng"] == "Ra":
                if not session_id:
                    raise ValueError("Vui lòng chọn lượt vào cần ghép với xe ra.")
                open_sessions = self.get_open_sessions()
                session = open_sessions[open_sessions["Mã phiên"] == session_id]
                if len(session) != 1:
                    raise ValueError("Lượt vào đã được ghép hoặc không còn tồn tại. Hãy làm mới danh sách.")
                entry = session.iloc[0]
                staff = self.find_staff_by_plate(normalized_plate)
                employee_id = staff["Mã nhân viên"] if staff else ""
                vehicle_type = "Nhân viên" if staff else "Khách vãng lai"
                entry_indices = frame.index[frame["Mã lượt"] == entry["Mã lượt"]]
                frame.loc[entry_indices, "Biển số"] = normalized_plate
                frame.loc[entry_indices, "Mã nhân viên"] = employee_id
                frame.loc[entry_indices, "Loại xe"] = vehicle_type
                frame.loc[entry_indices, "Trạng thái"] = "Đã ra"
                frame.loc[index, "Biển số"] = normalized_plate
                frame.loc[index, "Mã nhân viên"] = employee_id
                frame.loc[index, "Loại xe"] = vehicle_type
                frame.loc[index, "Mã phiên"] = session_id
                frame.loc[index, "Trạng thái"] = "Đã đối chiếu"
            else:
                raise ValueError(f"Loại cổng không hợp lệ: {row['Cổng']}")

            self._write_frame(frame.loc[:, LOG_COLUMNS], self.logs_path)

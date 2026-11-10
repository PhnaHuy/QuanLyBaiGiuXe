from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2


class CaptureStorageError(Exception):
    pass


class CaptureStorage:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.capture_directory = self.directory / "captures"

    def save_capture(self, event_id, frame, plate=None, vehicle=None):
        day_directory = datetime.now().strftime("%Y/%m/%d")
        relative_paths = {}
        images = {
            "Ảnh toàn cảnh": frame,
            "Ảnh biển số": plate,
            "Ảnh xe": vehicle,
        }

        try:
            for label, image in images.items():
                if image is None or image.size == 0:
                    relative_paths[label] = ""
                    continue
                suffix = {
                    "Ảnh toàn cảnh": "frame",
                    "Ảnh biển số": "plate",
                    "Ảnh xe": "vehicle",
                }[label]
                relative_path = (
                    Path("captures")
                    / day_directory
                    / f"{event_id}_{suffix}.jpg"
                )
                target = self.directory / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                success, encoded = cv2.imencode(".jpg", image)
                if not success:
                    raise CaptureStorageError(
                        f"Không thể mã hóa ảnh {suffix} để lưu."
                    )
                temporary = target.with_name(
                    f"{target.stem}_{uuid4().hex}.tmp"
                )
                try:
                    temporary.write_bytes(encoded.tobytes())
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
                relative_paths[label] = relative_path.as_posix()
        except (OSError, cv2.error, CaptureStorageError) as error:
            self.remove_capture(relative_paths)
            if isinstance(error, CaptureStorageError):
                raise
            raise CaptureStorageError(f"Không thể lưu ảnh lượt xe: {error}") from error

        return relative_paths

    def remove_capture(self, paths):
        for path in paths.values():
            if not path:
                continue
            target = (self.directory / Path(path)).resolve()
            try:
                target.relative_to(self.capture_directory.resolve())
            except ValueError:
                continue
            target.unlink(missing_ok=True)

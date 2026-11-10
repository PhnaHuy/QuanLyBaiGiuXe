import os
import re
import unicodedata
from pathlib import Path
from threading import Lock

import cv2
import numpy as np


class ANPRError(Exception):
    pass


_ENGINE = None
_PLATE_DETECTOR = None
_PLATE_CLASS_IDS = frozenset()
_ENGINE_LOCK = Lock()
_DETECTOR_LOCK = Lock()
_INFERENCE_LOCK = Lock()
_TORCH_CONFIGURED = False
_YOLO_DEVICE = "cpu"
_PLATE_PATTERN = re.compile(r"^\d{2}[A-Z][A-Z0-9]{4,7}$")
_APP_DIRECTORY = Path(__file__).resolve().parent
_PROJECT_MODEL_PATH = _APP_DIRECTORY / "models" / "license_plate_yolov8n.pt"
_YOLO_IMAGE_SIZE = 640
_YOLO_CONFIDENCE = 0.25
_MAX_PLATE_CROPS = 3
_OCR_DETECTION_SIDE = 256
_OCR_FALLBACK_DETECTION_SIDE = 384
_PLATE_CLASS_MARKERS = ("plate", "bienso", "biensoxe", "numberplate")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


def normalize_plate(text):
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def _normalize_class_name(text):
    without_accents = unicodedata.normalize("NFKD", str(text))
    ascii_text = "".join(
        character for character in without_accents
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^A-Z0-9]", "", ascii_text.upper())


def _resolve_detector_path():
    configured_path = os.environ.get("PARKING_PLATE_MODEL")
    if configured_path:
        path = Path(configured_path).expanduser()
        if path.is_file():
            return path
        raise ANPRError(
            f"Không tìm thấy model YOLO được cấu hình tại: {path}. "
            "Hãy kiểm tra biến PARKING_PLATE_MODEL."
        )

    if _PROJECT_MODEL_PATH.is_file():
        return _PROJECT_MODEL_PATH

    raise ANPRError(
        "Không tìm thấy model YOLO nhận diện biển số. Hãy đặt tệp tại "
        f"“{_PROJECT_MODEL_PATH}” hoặc cấu hình biến PARKING_PLATE_MODEL."
    )


def _get_plate_detector():
    global _PLATE_DETECTOR, _PLATE_CLASS_IDS, _TORCH_CONFIGURED, _YOLO_DEVICE
    with _DETECTOR_LOCK:
        if _PLATE_DETECTOR is None:
            model_path = _resolve_detector_path()
            try:
                import torch
                from ultralytics import YOLO
            except ImportError as error:
                raise ANPRError(
                    "Chưa cài Ultralytics/PyTorch. Hãy cài các gói trong requirements.txt "
                    "bằng Python 3.13 của môi trường .venv."
                ) from error

            try:
                if not _TORCH_CONFIGURED:
                    if torch.cuda.is_available():
                        _YOLO_DEVICE = 0
                    else:
                        torch.set_num_threads(min(4, os.cpu_count() or 1))
                        try:
                            torch.set_num_interop_threads(1)
                        except RuntimeError:
                            pass
                    _TORCH_CONFIGURED = True
                detector = YOLO(str(model_path))
                names = detector.names
                if isinstance(names, dict):
                    named_classes = names.items()
                else:
                    named_classes = enumerate(names)
                plate_class_ids = [
                    int(class_id)
                    for class_id, name in named_classes
                    if any(
                        marker in _normalize_class_name(name)
                        for marker in _PLATE_CLASS_MARKERS
                    )
                ]
                if not plate_class_ids and len(names) == 1:
                    plate_class_ids = [0]
                if not plate_class_ids:
                    labels = ", ".join(str(name) for name in names.values()) if isinstance(names, dict) else ", ".join(names)
                    raise ANPRError(
                        "Tệp YOLO được chọn không có lớp nhận diện biển số. "
                        f"Các nhãn model hiện có: {labels}. Hãy dùng checkpoint đã train "
                        "cho biển số (thường là best.pt), không dùng weights YOLO COCO gốc."
                    )
                _PLATE_CLASS_IDS = frozenset(plate_class_ids)
                detector.model.eval()
                _PLATE_DETECTOR = detector
            except ANPRError:
                raise
            except Exception as error:
                raise ANPRError(f"Không thể nạp model YOLO biển số: {error}") from error
        return _PLATE_DETECTOR


def _get_ocr_engine():
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as error:
                raise ANPRError(
                    "Chưa cài PaddleOCR hoặc môi trường Python không tương thích. "
                    "Hãy dùng Python 3.10–3.13 64-bit và cài các gói trong requirements.txt."
                ) from error

            try:
                _ENGINE = PaddleOCR(
                    device="cpu",
                    enable_mkldnn=False,
                    text_detection_model_name="PP-OCRv6_tiny_det",
                    text_recognition_model_name="PP-OCRv6_tiny_rec",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    text_det_limit_side_len=_OCR_DETECTION_SIDE,
                    cpu_threads=min(4, os.cpu_count() or 1),
                )
            except Exception as error:
                raise ANPRError(
                    f"Không thể khởi tạo PaddleOCR. Hãy kiểm tra kết nối tải model và cấu hình PaddlePaddle: {error}"
                ) from error
        return _ENGINE


def _detect_plate_crops(image):
    detector = _get_plate_detector()
    try:
        predictions = detector.predict(
            source=image,
            imgsz=_YOLO_IMAGE_SIZE,
            conf=_YOLO_CONFIDENCE,
            iou=0.45,
            max_det=_MAX_PLATE_CROPS,
            device=_YOLO_DEVICE,
            verbose=False,
        )
    except Exception as error:
        raise ANPRError(f"Model YOLO không thể định vị biển số: {error}") from error

    if not predictions:
        return []

    boxes = predictions[0].boxes
    if boxes is None or len(boxes) == 0:
        return []

    detections = sorted(
        (
            (box, confidence)
            for box, confidence, class_id in zip(
                boxes.xyxy.cpu().numpy(),
                boxes.conf.cpu().numpy(),
                boxes.cls.cpu().numpy(),
            )
            if int(class_id) in _PLATE_CLASS_IDS
        ),
        key=lambda detection: float(detection[1]),
        reverse=True,
    )
    image_height, image_width = image.shape[:2]
    crops = []
    for box, _confidence in detections[:_MAX_PLATE_CROPS]:
        x1, y1, x2, y2 = (float(value) for value in box)
        box_width = max(x2 - x1, 1)
        box_height = max(y2 - y1, 1)
        padding_x = max(4, int(box_width * 0.12))
        padding_y = max(4, int(box_height * 0.18))
        left = max(0, int(x1) - padding_x)
        top = max(0, int(y1) - padding_y)
        right = min(image_width, int(x2) + padding_x)
        bottom = min(image_height, int(y2) + padding_y)
        crop = image[top:bottom, left:right]
        if crop.size:
            vehicle_left = max(0, int(x1 - box_width * 2.5))
            vehicle_top = max(0, int(y1 - box_height * 3))
            vehicle_right = min(image_width, int(x2 + box_width * 2.5))
            vehicle_bottom = min(image_height, int(y2 + box_height * 4))
            vehicle_crop = image[
                vehicle_top:vehicle_bottom,
                vehicle_left:vehicle_right,
            ]
            crops.append((crop.copy(), vehicle_crop.copy()))
    return crops


def _result_data(result):
    data = getattr(result, "json", result)
    if callable(data):
        data = data()
    if isinstance(data, dict) and isinstance(data.get("res"), dict):
        return data["res"]
    return data if isinstance(data, dict) else {}


def _box_bounds(box):
    try:
        points = [(float(point[0]), float(point[1])) for point in box]
        if not points:
            return None
        xs, ys = zip(*points)
    except (TypeError, ValueError, IndexError):
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _plate_candidates(result):
    data = _result_data(result)
    texts = data.get("rec_texts", [])
    scores = data.get("rec_scores", [])
    boxes = data.get("rec_polys", data.get("dt_polys", []))

    fragments = []
    for index, text in enumerate(texts):
        plate = normalize_plate(text)
        if not plate:
            continue
        try:
            score = float(scores[index]) if index < len(scores) else 0.0
        except (TypeError, ValueError):
            score = 0.0
        box = _box_bounds(boxes[index]) if index < len(boxes) else None
        fragments.append((plate, score, box))

    candidates = [
        (text, score)
        for text, score, _ in fragments
        if _PLATE_PATTERN.fullmatch(text)
    ]

    for index, (first, first_score, first_box) in enumerate(fragments):
        if first_box is None:
            continue
        for second, second_score, second_box in fragments[index + 1:]:
            if second_box is None:
                continue
            first_x1, first_y1, first_x2, first_y2 = first_box
            second_x1, second_y1, second_x2, second_y2 = second_box
            first_height = max(first_y2 - first_y1, 1)
            second_height = max(second_y2 - second_y1, 1)
            height = max(first_height, second_height)
            horizontal_gap = max(
                second_x1 - first_x2,
                first_x1 - second_x2,
                0,
            )
            vertical_gap = max(
                second_y1 - first_y2,
                first_y1 - second_y2,
                0,
            )
            if horizontal_gap > height * 8 or vertical_gap > height * 3:
                continue

            ordered_texts = sorted(
                ((first, first_box), (second, second_box)),
                key=lambda item: (
                    (item[1][1] + item[1][3]) / 2,
                    (item[1][0] + item[1][2]) / 2,
                ),
            )
            combined = "".join(text for text, _ in ordered_texts)
            if _PLATE_PATTERN.fullmatch(combined):
                candidates.append((combined, (first_score + second_score) / 2))

    return candidates


def recognize_plate(image, on_crop_detected=None):
    if image is None or image.size == 0:
        raise ANPRError("Không có ảnh hợp lệ để nhận diện.")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ANPRError("Ảnh đầu vào phải có đủ ba kênh màu.")

    try:
        with _INFERENCE_LOCK:
            crops = _detect_plate_crops(image)
            if not crops:
                raise ANPRError(
                    "YOLO không phát hiện biển số trong ảnh. Hãy kiểm tra vị trí/góc camera, "
                    "độ rõ của biển số và ngưỡng phát hiện của model."
                )

            engine = None
            for crop_index, (crop, vehicle_crop) in enumerate(crops):
                if on_crop_detected is not None:
                    on_crop_detected(crop, vehicle_crop)
                if engine is None:
                    engine = _get_ocr_engine()
                prepared = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                results = engine.predict(
                    prepared,
                    text_det_limit_side_len=_OCR_DETECTION_SIDE,
                )
                candidates = [
                    candidate
                    for result in results
                    for candidate in _plate_candidates(result)
                ]
                if candidates:
                    return max(candidates, key=lambda candidate: candidate[1])[0]

                if crop_index == 0:
                    fallback_results = engine.predict(
                        prepared,
                        text_det_limit_side_len=_OCR_FALLBACK_DETECTION_SIDE,
                    )
                    fallback_candidates = [
                        candidate
                        for result in fallback_results
                        for candidate in _plate_candidates(result)
                    ]
                    if fallback_candidates:
                        return max(
                            fallback_candidates,
                            key=lambda candidate: candidate[1],
                        )[0]
    except ANPRError:
        raise
    except Exception as error:
        raise ANPRError(f"Không thể nhận diện biển số bằng YOLO/PaddleOCR: {error}") from error

    raise ANPRError(
        "Đã tìm thấy vùng biển số nhưng OCR chưa đọc được ký tự. "
        "Hãy kiểm tra độ nét và độ sáng của ảnh."
    )


def initialize_models():
    with _INFERENCE_LOCK:
        detector = _get_plate_detector()
        detector.predict(
            source=np.zeros((320, 320, 3), dtype=np.uint8),
            imgsz=_YOLO_IMAGE_SIZE,
            conf=_YOLO_CONFIDENCE,
            device=_YOLO_DEVICE,
            verbose=False,
        )
        engine = _get_ocr_engine()
        engine.predict(np.zeros((96, 320, 3), dtype=np.uint8))

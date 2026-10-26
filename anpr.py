import re

import cv2
import pytesseract


class ANPRError(Exception):
    pass


def normalize_plate(text):
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def recognize_plate(image):
    if image is None or image.size == 0:
        raise ANPRError("Không có ảnh hợp lệ để nhận diện.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    prepared = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    try:
        text = pytesseract.image_to_string(
            prepared,
            config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        )
    except pytesseract.TesseractNotFoundError as error:
        raise ANPRError(
            "Không tìm thấy Tesseract OCR. Hãy cài đặt Tesseract và thêm chương trình vào PATH."
        ) from error
    except pytesseract.TesseractError as error:
        raise ANPRError(f"OCR không thể xử lý ảnh: {error}") from error

    plate = normalize_plate(text)
    if len(plate) < 5:
        raise ANPRError(
            "Không đọc được biển số rõ ràng. Hãy kiểm tra góc chụp, ánh sáng và vị trí xe."
        )
    return plate

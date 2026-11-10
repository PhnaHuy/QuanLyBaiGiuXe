---
name: anpr-pipeline-maintainer
description: 'Use when changing or debugging vehicle license-plate detection, YOLO checkpoint loading, PaddleOCR, plate normalization, or ANPR accuracy and performance in anpr.py.'
---

# ANPR Pipeline Maintainer

## When to Use

- Modifying `anpr.py` or the flow that recognizes a plate from an image.
- Investigating model-loading, YOLO detection, OCR, or plate-format issues.
- Changing model configuration, preprocessing, inference synchronization, or recognition performance.

## Procedure

1. Trace the full path from the caller in `ui.py` to `recognize_plate()` and back. Identify whether the incoming frame is BGR and preserve the existing color conversion expected by each library.
2. Preserve model resolution behavior: `PARKING_PLATE_MODEL` is an optional override; otherwise resolve `models\license_plate_yolov8n.pt` relative to `anpr.py`. Never add a developer-machine absolute path.
3. Validate that a loaded YOLO checkpoint is suitable for license-plate detection. Do not silently substitute generic COCO weights or treat a failed model load as a successful no-detection result.
4. Preserve the established pipeline: detect plate regions with YOLO, crop valid bounds, pass crops to PaddleOCR, normalize OCR text, and return a valid plate candidate or a clear `ANPRError`.
5. Keep shared-model initialization and inference synchronization safe. Do not change lock scope, worker assumptions, or device configuration without checking all callers and concurrent paths.
6. Handle initialization, inference, and invalid-image failures explicitly. Keep user-facing errors actionable and avoid hiding the original cause.
7. Verify the changed path directly: resolve and load the configured/default checkpoint when available, test relevant recognition helpers with representative inputs, and cover a clear failure case. Avoid modifying live Excel files for recognition tests.
8. Update `README.md` when model files, setup, network requirements, configuration, or recognition behavior changes.

## Invariants

- The bundled detector checkpoint is `models\license_plate_yolov8n.pt`.
- `PARKING_PLATE_MODEL` remains an explicit override and an invalid configured path remains an error.
- PaddleOCR may download its own model on first use; it is separate from the bundled YOLO checkpoint.
- Recognition failure must not create a success-shaped plate or a parking log entry.

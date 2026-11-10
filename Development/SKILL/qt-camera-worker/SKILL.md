---
name: qt-camera-worker
description: 'Use when implementing, debugging, or refactoring PySide6 camera/video capture, QThread workers, UI signals, frame display, or resource shutdown in this application.'
---

# Qt Camera and Worker Lifecycle

## When to Use

- Changing `camera_thread.py`, `GatePanel`, or background workers in `ui.py`.
- Fixing camera/video startup, frame delivery, capture, shutdown, or UI responsiveness.
- Adding a long-running task that interacts with the Qt interface.

## Procedure

1. Trace ownership and lifecycle from the widget that creates a worker through start, signal connections, completion, and window shutdown.
2. Keep camera reads and other blocking work off the UI thread. Deliver results and errors through Qt signals; do not update widgets directly from a worker thread.
3. Preserve source semantics: a numeric webcam index is an integer source; a selected video path is a string source. Validate paths before starting capture.
4. Protect shared frame access. Return a copy of the latest frame so recognition cannot race with the camera overwriting its buffer.
5. Release `cv2.VideoCapture` on normal completion, read failure, exception, and requested stop. Report source failures through the existing signals and UI feedback.
6. On source replacement or window close, request a stop and wait for the worker before discarding it. Do not leave a running QThread detached from its owner.
7. Prevent duplicate in-flight recognition for the same gate and ensure controls are restored on both success and failure.
8. Validate lifecycle paths where possible: successful startup, failed startup/read, video end, stop/restart, worker failure, and application close. Use mocks or a temporary video when physical camera access is unavailable.

## Invariants

- UI updates happen on the Qt UI thread through signal/slot delivery.
- A worker must not outlive resources it accesses.
- A failed capture or recognition is presented as an error, not as a successful empty result.
- Preserve existing user-visible messages and Vietnamese terminology unless the requested behavior changes.

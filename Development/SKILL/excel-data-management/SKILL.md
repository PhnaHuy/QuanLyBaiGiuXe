---
name: excel-data-management
description: 'Use when changing, debugging, or testing staff records, parking logs, Excel schemas, validation, lookup, import/export, or persistence through ExcelDatabase.'
---

# Excel Data Management

## When to Use

- Modifying `excel_db.py` or callers that read, write, or export staff and parking-log data.
- Changing the schema, validation, duplicate handling, plate lookup, or Excel error reporting.
- Investigating data loss, locked workbooks, malformed files, or inconsistent records.

## Procedure

1. Read the relevant `ExcelDatabase` operation and its UI callers before editing. Preserve existing data and inspect the current worktree for unrelated changes.
2. Keep all access to `staff.xlsx` and `parking_logs.xlsx` behind `ExcelDatabase`; UI code should use its methods rather than opening these files directly.
3. Preserve the current schemas unless a requirement explicitly changes them:
   - Staff: `Mã nhân viên`, `Tên nhân viên`, `Biển số xe`.
   - Logs: `Thời gian`, `Biển số`, `Cổng`, `Loại xe`, `Mã nhân viên`, `Mã lượt`, `Mã phiên`, `Trạng thái`, `Biển số OCR`, ảnh và lỗi nhận diện.
4. Validate staff records before writing. Retain the required-field checks, unique employee IDs, and plate uniqueness based on `normalize_plate()`.
5. Preserve old parking logs when staff records are updated or deleted. Do not silently truncate, reorder, or rewrite unrelated data.
6. Keep reads and writes synchronized using the existing database lock. Convert file, permission, and schema errors into explicit `ExcelDatabaseError` messages that the UI can present.
7. Test with temporary files or a temporary directory. Verify valid CRUD/lookup behavior, duplicate and missing-field rejection, required columns, and locked/unreadable file handling as applicable.
8. For export changes, verify both `.xlsx` and `.csv` behavior and preserve the user's selected destination and format.
9. Update user documentation if the schema, storage location, backup expectations, or export behavior changes.

## Invariants

- A missing workbook may be initialized with its expected headers; an existing malformed workbook must not be silently treated as valid.
- Plate comparisons use the shared `normalize_plate()` function.
- Older parking logs may lack the newer event, session, status, and image columns; read them with compatible empty values and preserve all existing rows.
- Image files live under `captures/` and are referenced by relative paths in the parking log. Do not write image bytes into Excel or let tests modify the project's real captures.
- Errors must not be swallowed, and a failed write must never be reported as a successful operation.
- Tests must not overwrite the project's real `staff.xlsx` or `parking_logs.xlsx`.

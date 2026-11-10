---
name: clean-code-enforcer
description: 'Apply the project''s Python clean-code and architecture standards when implementing, refactoring, debugging, or reviewing code in the parking-management application.'
---

# Clean Code Enforcer

## When to Use

- Implementing or changing Python behavior in this project.
- Refactoring code for clarity, maintainability, or module boundaries.
- Debugging a defect that may span the UI, camera, ANPR, or Excel data modules.
- Reviewing a proposed change for consistency with existing project patterns.

## Procedure

1. Read the target code and its callers before editing. Check `git status` and preserve existing staged and unstaged work.
2. Keep changes in the module responsible for the behavior:
   - `main.py`: application startup and dependency wiring.
   - `ui.py`: widgets, user interaction, presentation, and orchestration.
   - `camera_thread.py`: camera/video capture and frame delivery.
   - `anpr.py`: plate detection, OCR, and recognition results.
   - `excel_db.py`: Excel persistence and data rules.
3. Prefer a small, complete change that fits current patterns. Extract a helper only when it clarifies a distinct responsibility or removes meaningful duplication.
4. Use descriptive Python names and PEP 8 style. Keep user-facing text in Vietnamese, consistent with the application.
5. Validate input and preserve explicit failures. Catch errors at a boundary where they can be handled; do not silently ignore failures or report success after a failed operation.
6. Preserve thread safety, resource cleanup, existing Excel columns, and public interfaces unless the requirement explicitly changes them. Update all callers when an interface must change.
7. Add or update tests when the repository provides a relevant test path. Otherwise run the smallest direct verification of the changed behavior and state any unverified cases.
8. Update `README.md` when installation, configuration, model requirements, or user-visible behavior changes.

## Clean-Code Checks

- Each function and class has a clear responsibility; avoid deeply nested conditionals and duplicated business rules.
- Use `pathlib.Path` and project-relative defaults; do not add machine-specific absolute paths.
- Use type hints where they clarify new interfaces or complex data, without casts that hide invalid assumptions.
- Do not use placeholders, success-shaped fallbacks, or comments in place of requested implementation.
- Keep error messages actionable and aligned with existing exception and UI-notification patterns.
- Do not add a framework, dependency, abstraction, or unrelated cleanup without a concrete need.

## Completion

Summarize the behavior changed, files affected, verification performed, and any remaining limitations. Do not claim a test or check was run unless it was.

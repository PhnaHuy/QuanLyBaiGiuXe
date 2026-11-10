import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from auth import ADMIN_DEFAULT_PASSWORD
from excel_db import ExcelDatabase, ExcelDatabaseError
from ui import LoginDialog, MainWindow, configure_light_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Quản lý bãi giữ xe")
    app.setQuitOnLastWindowClosed(False)
    configure_light_theme(app)

    login_dialog = LoginDialog()
    if login_dialog.exec() != login_dialog.DialogCode.Accepted:
        return 0

    data_directory = Path(__file__).resolve().parent
    database = ExcelDatabase(
        data_directory,
        staff_password=ADMIN_DEFAULT_PASSWORD,
    )
    try:
        database.initialize()
    except (ExcelDatabaseError, OSError) as error:
        QMessageBox.critical(
            None,
            "Không thể khởi động",
            f"Không thể chuẩn bị dữ liệu Excel:\n{error}",
        )
        return 1

    window_holder = {"window": None}
    retired_windows = []

    def open_session(role):
        window = MainWindow(database, role)
        window.logout_requested.connect(return_to_login)
        window.window_closed.connect(app.quit)
        window_holder["window"] = window
        window.show()

    def retire_window(window):
        retired_windows.append(window)

        def finish_retirement():
            window.close()
            retired_windows.remove(window)

        window.logout_cleanup_finished.connect(finish_retirement)
        window.prepare_for_logout()

    def return_to_login():
        previous_window = window_holder["window"]
        if previous_window is not None:
            previous_window.hide()
        login_dialog = LoginDialog()
        if login_dialog.exec() != login_dialog.DialogCode.Accepted:
            if previous_window is not None:
                previous_window.show()
            return

        open_session(login_dialog.selected_role)
        if previous_window is not None:
            retire_window(previous_window)

    open_session(login_dialog.selected_role)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

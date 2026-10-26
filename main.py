import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from excel_db import ExcelDatabase, ExcelDatabaseError
from ui import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Quản lý bãi giữ xe")

    data_directory = Path(__file__).resolve().parent
    database = ExcelDatabase(data_directory)
    try:
        database.initialize()
    except (ExcelDatabaseError, OSError) as error:
        QMessageBox.critical(
            None,
            "Không thể khởi động",
            f"Không thể chuẩn bị dữ liệu Excel:\n{error}",
        )
        return 1

    window = MainWindow(database)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

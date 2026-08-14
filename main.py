import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow
from core.logger import get_logger

logger = get_logger("app")


def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Uncaught exception:\n{error_msg}")
    sys.__excepthook__(exctype, value, tb)


def main():
    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName("WeMark")
    app.setApplicationDisplayName("微墨 (WeMark)")
    app.setOrganizationName("WeMarkTeam")

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Application crash: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

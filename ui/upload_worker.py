from PySide6.QtCore import QThread, Signal

from core.image_hosting import replace_local_images
from core.logger import get_logger

logger = get_logger("upload_worker")


class ImageUploadWorker(QThread):
    done = Signal(str, int)
    error = Signal(str)

    def __init__(self, html: str, base_path: str = None, parent=None):
        super().__init__(parent)
        self._html = html
        self._base_path = base_path

    def run(self):
        try:
            new_html, count, _ = replace_local_images(self._html, self._base_path)
            self.done.emit(new_html, count)
        except Exception as e:
            logger.error(f"Image upload failed: {e}", exc_info=True)
            self.error.emit(str(e))
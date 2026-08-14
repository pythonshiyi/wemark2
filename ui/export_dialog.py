from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QFileDialog, QMessageBox, QApplication,
)

from core.i18n import tr
from core.renderer import render_full_page, render_html, _load_template, strip_max_width, _fix_local_image_paths


class ExportDialog(QDialog):
    def __init__(self, parent, markdown: str, template: str, base_path: str = None):
        super().__init__(parent)
        self.setWindowTitle(f"📦 {tr('export_title')}")
        self.setMinimumWidth(420)
        self.setStyleSheet(
            "QDialog{background:#fff;}"
            "QPushButton{padding:10px 20px;font-size:13px;border-radius:6px;"
            "text-align:left;}"
        )

        self._markdown = markdown
        self._template = template
        self._base_path = base_path
        self._html = render_html(markdown, template)
        self._exporting = False

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)

        layout.addWidget(QLabel(tr("export_select"), styleSheet="font-weight:bold;color:#555;font-size:13px;"))

        btn_style = "QPushButton{background:#f8f9fa;border:1px solid #e0e0e0;}"
        btn_style += "QPushButton:hover{background:#e8f0fe;border-color:#1a73e8;}"

        btn_pdf = QPushButton(f"📄 {tr('export_pdf_btn')}")
        btn_pdf.setStyleSheet(btn_style)
        btn_pdf.clicked.connect(lambda: self._export("pdf"))
        layout.addWidget(btn_pdf)

        btn_img = QPushButton(f"🖼 {tr('export_image_btn')}")
        btn_img.setStyleSheet(btn_style)
        btn_img.clicked.connect(lambda: self._export("image"))
        layout.addWidget(btn_img)

        btn_wx = QPushButton(f"📋 {tr('export_wechat_btn')}")
        btn_wx.setStyleSheet(
            "QPushButton{background:#07C160;color:white;font-weight:bold;}"
            "QPushButton:hover{background:#06AD56;}"
        )
        btn_wx.clicked.connect(self._copy_wechat)
        layout.addWidget(btn_wx)

        btn_html = QPushButton(f"📝 {tr('export_html_btn')}")
        btn_html.setStyleSheet(btn_style)
        btn_html.clicked.connect(self._copy_html)
        layout.addWidget(btn_html)

        self._progress = QProgressBar(visible=False,
            styleSheet="QProgressBar{border:1px solid #e0e0e0;border-radius:4px;"
                       "text-align:center;font-size:10px;height:18px;}"
                       "QProgressBar::chunk{background:#1a73e8;border-radius:3px;}")
        layout.addWidget(self._progress)

        layout.addStretch()

        btn_close = QPushButton(tr("export_close"))
        btn_close.setStyleSheet("QPushButton{background:transparent;color:#999;border:none;}"
                                "QPushButton:hover{color:#333;}")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def _export(self, fmt: str):
        if self._exporting:
            return
        if fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, tr("save_pdf_dialog"), "", "PDF (*.pdf)")
        else:
            path, _ = QFileDialog.getSaveFileName(self, tr("image_export_dialog"), "", "PNG (*.png)")
        if not path:
            return

        self._exporting = True
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self.setEnabled(False)

        QApplication.processEvents()

        try:
            if fmt == "pdf":
                self._export_pdf(path)
            else:
                self._export_image(path)
            self._on_export_done(path)
        except Exception as e:
            self._on_export_error(str(e))

    def _export_pdf(self, path: str):
        template = _load_template(self._template)
        page_style = template.get("_page_style", "")
        page_style = strip_max_width(page_style)

        full_html = (
            f"<html><head><meta charset='utf-8'><style>"
            f"body {{ width:650px; {page_style} }}"
            f"</style></head><body>{self._html}</body></html>"
        )

        doc = QTextDocument()
        doc.setHtml(full_html)
        doc.setTextWidth(650)

        printer = QPrinter()
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPrinter.A4)
        printer.setPageMargins(20, 20, 20, 20, QPrinter.Millimeter)
        doc.print(printer)

    def _export_image(self, path: str):
        template = _load_template(self._template)
        page_style = template.get("_page_style", "")
        page_style = strip_max_width(page_style)

        full_html = (
            f"<html><head><meta charset='utf-8'><style>"
            f"body {{ width:540px; {page_style} }}"
            f"</style></head><body>{self._html}</body></html>"
        )

        doc = QTextDocument()
        doc.setHtml(full_html)
        doc.setTextWidth(540)

        dpi = 2
        doc_w = int(doc.size().width())
        doc_h = int(doc.size().height())
        if doc_w < 1 or doc_h < 1:
            raise RuntimeError("Empty document, nothing to export")
        img_w = doc_w * dpi
        img_h = doc_h * dpi

        pixmap = QPixmap(img_w, img_h)
        pixmap.fill(QColor("#ffffff"))
        painter = None
        try:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.TextAntialiasing)
            painter.scale(dpi, dpi)
            doc.drawContents(painter)
        finally:
            if painter:
                painter.end()

        pixmap.save(path, "PNG")

    def _on_export_done(self, path: str):
        self._progress.setVisible(False)
        self.setEnabled(True)
        self._exporting = False
        QMessageBox.information(self, tr("export_success"), tr("export_success_msg").format(path))
        self.accept()

    def _on_export_error(self, err: str):
        self._progress.setVisible(False)
        self.setEnabled(True)
        self._exporting = False
        QMessageBox.warning(self, tr("export_failed"), tr("export_failed_msg").format(err))

    def _copy_wechat(self):
        from core.clipboard import copy_rich_text
        full_html = render_full_page(self._markdown, self._template)
        copy_rich_text(full_html, self._base_path)
        QMessageBox.information(self, tr("copy_done"), tr("copy_wechat_done"))

    def _copy_html(self):
        import pyperclip
        pyperclip.copy(self._html)
        QMessageBox.information(self, tr("copy_done"), tr("copy_html_done"))

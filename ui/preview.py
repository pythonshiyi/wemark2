from pathlib import Path

from PySide6.QtCore import QUrl, Signal, QObject, QThread
from PySide6.QtGui import QPixmap, QPainter, QColor, QTextDocument
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel

from core.config import config_manager as _cfg
from core.logger import get_logger
from core.renderer import render_html, render_full_page, strip_max_width, _fix_local_image_paths


class PreviewRenderWorker(QThread):
    rendered = Signal(int, str)

    def __init__(self, markdown: str, template: str, gen: int, parent=None):
        super().__init__(parent)
        self._markdown = markdown
        self._template = template
        self._gen = gen

    def run(self):
        try:
            html = render_full_page(self._markdown, self._template)
            self.rendered.emit(self._gen, html)
        except Exception as e:
            get_logger("preview").error(f"Preview render failed: {e}", exc_info=True)


class _ScrollBridge(QObject):
    scroll_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

    def notify_scroll(self, pct: float):
        self.scroll_changed.emit(pct)


class Preview(QWidget):
    IMG_DPI = 2
    IMG_WIDTH = 540

    scroll_percent_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._webview = QWebEngineView()
        layout.addWidget(self._webview)

        self._scroll_bridge = _ScrollBridge()
        self._scroll_bridge.scroll_changed.connect(self._on_web_scroll)
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._scroll_bridge)
        self._webview.page().setWebChannel(self._channel)

        settings = self._webview.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, False)

        self._current_template = _cfg.get("template.last_used", "default")
        self._webview.loadFinished.connect(self._on_page_loaded)
        self._webview.setHtml(self._full_page_html(""))

    def _on_page_loaded(self, ok: bool):
        if ok:
            self._inject_scroll_js()

    def _on_web_scroll(self, pct: float):
        self.scroll_percent_changed.emit(pct)

    def _full_page_html(self, markdown: str) -> str:
        html = render_full_page(markdown, self._current_template)
        return self._apply_theme_css(html)

    def _apply_theme_css(self, html: str) -> str:
        if _cfg.get("theme", "light") != "dark":
            return html
        dark_css = (
            "<style>"
            "body{background:#1e1e2e;color:#cdd6f4 !important;}"
            "h1,h2,h3,h4,h5,h6{color:#89b4fa !important;}"
            "a{color:#89b4fa !important;}"
            "code,pre{background:#313244 !important;color:#cdd6f4 !important;}"
            "blockquote{background:#2a2a3c !important;border-left-color:#89b4fa !important;}"
            "table tr{background:#1e1e2e !important;}"
            "table tr:nth-child(even){background:#2a2a3c !important;}"
            "table td,table th{border-color:#45475a !important;}"
            ".mermaid{background:#2a2a3c !important;}"
            "img{opacity:0.9;}"
            "</style>"
        )
        return html.replace("</head>", dark_css + "</head>", 1)

    def render(self, markdown: str, template_name: str = None):
        if template_name is not None:
            self._current_template = template_name
        self.display_html(self._full_page_html(markdown))

    def display_html(self, html: str):
        html = self._apply_theme_css(html)
        home = Path.home()
        base_url = QUrl.fromLocalFile(str(home / ".wemark2"))
        self._webview.setHtml(html, base_url)

    def capture_to_clipboard(self, markdown: str):
        html = render_html(markdown, self._current_template)
        self._render_to_clipboard(html)

    def _render_to_clipboard(self, body_html: str):
        from core.renderer import _load_template

        body_html = _fix_local_image_paths(body_html)
        template = _load_template(self._current_template)
        page_style = template.get("_page_style", "")
        page_style = strip_max_width(page_style)

        full_html = (
            f"<html><head><meta charset='utf-8'><style>"
            f"body {{ width:{self.IMG_WIDTH}px; {page_style} }}"
            f"</style></head><body>{body_html}</body></html>"
        )

        doc = QTextDocument()
        doc.setDefaultFont(self._webview.font())
        doc.setHtml(full_html)
        doc.setTextWidth(self.IMG_WIDTH)

        doc_w = int(doc.size().width())
        doc_h = int(doc.size().height())
        if doc_w < 1 or doc_h < 1:
            QApplication.clipboard().setText("")
            return

        img_w = doc_w * self.IMG_DPI
        img_h = doc_h * self.IMG_DPI

        pixmap = QPixmap(img_w, img_h)
        pixmap.fill(QColor("#ffffff"))
        painter = None
        try:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.TextAntialiasing)
            painter.scale(self.IMG_DPI, self.IMG_DPI)
            doc.drawContents(painter)
        finally:
            if painter:
                painter.end()

        QApplication.clipboard().setPixmap(pixmap)

    def _inject_scroll_js(self):
        js = """
        (function() {
            if (window.__wemarkBridgeReady) return;
            window.__wemarkBridgeReady = true;
            window.__wemarkScrollPct = 0;
            window.__wemarkChannel = null;
            window.__wemarkNotifyScroll = function(pct) {
                if (window.__wemarkChannel) {
                    try { window.__wemarkChannel.objects.bridge.notify_scroll(pct); } catch(e) {}
                }
            };
            window.__wemarkScrollSync = function(pct) {
                var doc = document.documentElement;
                var body = document.body;
                var maxScroll = Math.max(
                    doc.scrollHeight - doc.clientHeight,
                    body.scrollHeight - body.clientHeight
                );
                window.scrollTo(0, maxScroll * pct);
                window.__wemarkScrollPct = pct;
            };
            try {
                new QWebChannel(qt.webChannelTransport, function(ch) {
                    window.__wemarkChannel = ch;
                });
            } catch(e) {}
            var ticking = false;
            window.addEventListener('scroll', function() {
                if (!ticking) {
                    window.requestAnimationFrame(function() {
                        var doc = document.documentElement;
                        var body = document.body;
                        var maxScroll = Math.max(
                            doc.scrollHeight - doc.clientHeight,
                            body.scrollHeight - body.clientHeight
                        );
                        var pct = maxScroll > 0 ? window.scrollY / maxScroll : 0;
                        window.__wemarkScrollPct = pct;
                        window.__wemarkNotifyScroll(pct);
                        ticking = false;
                    });
                    ticking = true;
                }
            }, {passive: true});
        })();
        """
        self._webview.page().runJavaScript(js)

    def set_scroll_percent(self, pct: float):
        pct = max(0.0, min(1.0, pct))
        js = f"window.__wemarkScrollSync({pct});"
        self._webview.page().runJavaScript(js)

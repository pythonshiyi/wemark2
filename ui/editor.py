import re
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer, QMimeData, QPoint
from PySide6.QtGui import (
    QTextCursor,
    QTextDocument,
    QTextOption,
    QPainter,
    QColor,
    QPalette,
    QFont,
    QPen,
    QTextFormat,
    QKeyEvent,
    QPixmap,
    QFontMetrics,
)
from PySide6.QtWidgets import QTextEdit, QMenu, QFileDialog, QWidget

from core.config import config_manager as _cfg
from core.i18n import tr


_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}


def _is_image_file(path: str) -> bool:
    return Path(path).suffix.lower() in _IMAGE_EXTS


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor
        self.setObjectName("LineNumberArea")
        self.setCursor(Qt.ArrowCursor)

    def paintEvent(self, event):
        self._editor._draw_line_numbers(event)
        super().paintEvent(event)


class Editor(QTextEdit):
    scroll_changed = Signal(float)
    cursor_line_changed = Signal(int, int)
    mode_changed = Signal()
    ai_action_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Editor")
        self.setAcceptRichText(False)
        self.setWordWrapMode(QTextOption.WordWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QTextEdit.NoFrame)

        self._line_number_area = LineNumberArea(self)
        self.document().setDocumentMargin(16)

        self._auto_pairs = {
            "(": ")", "[": "]", "{": "}", '"': '"', "*": "*", "_": "_", "`": "`",
            "「": "」", "《": "》", "'": "'", "『": "』", "【": "】",
        }
        self._current_line_bg = QColor("#e8f4fd")
        self._focus_mode = False
        self._typewriter_scroll = False
        self._last_typed = ""
        self._typing = False
        self._line_drag_anchor = -1

        from ui.markdown_highlighter import MarkdownHighlighter
        self.highlighter = MarkdownHighlighter(self.document())

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.textChanged.connect(self._on_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_moved)

        self._change_timer = QTimer(self)
        self._change_timer.setSingleShot(True)
        self._change_timer.setInterval(250)

        self.setCursorWidth(2)
        self._highlight_current_line()
        self._update_line_number_area()

    def _on_scroll(self, value: int):
        mx = self.verticalScrollBar().maximum()
        if mx > 0:
            self.scroll_changed.emit(value / mx)
        self._line_number_area.update()

    def _on_text_changed(self):
        self._change_timer.start()
        self._update_line_number_area()

    def _on_cursor_moved(self):
        self._highlight_current_line()
        if not self._typing:
            self._last_typed = ""
        if self._typewriter_scroll:
            self._center_cursor()
        cursor = self.textCursor()
        self.cursor_line_changed.emit(
            cursor.blockNumber() + 1,
            max(1, self.document().blockCount()),
        )

    def _center_cursor(self):
        cursor = self.textCursor()
        block_rect = self.cursorRect(cursor)
        viewport_height = self.viewport().height()
        sb = self.verticalScrollBar()
        cursor_center = block_rect.top() + block_rect.height() / 2
        target_center = viewport_height * 0.35
        sb.setValue(int(sb.value() + cursor_center - target_center))

    def set_on_change_callback(self, cb):
        try:
            self._change_timer.timeout.disconnect()
        except (TypeError, RuntimeError):
            pass
        self._change_timer.timeout.connect(cb)

    def get_markdown(self) -> str:
        return self.toPlainText()

    def _line_number_width(self) -> int:
        show = _cfg.get("editor.show_line_numbers", True)
        if not show:
            return 0
        line_font = QFont(self.font())
        line_font.setPointSize(max(8, self.font().pointSize() - 1))
        fm = QFontMetrics(line_font)
        digits = max(3, len(str(max(1, self.document().blockCount()))))
        return fm.horizontalAdvance("0" * digits) + 24

    def _update_line_number_area(self):
        width = self._line_number_width()
        self.setViewportMargins(width, 0, 0, 0)
        self._line_number_area.setFixedWidth(width)
        self._line_number_area.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            cr.left(), cr.top(), self._line_number_width(), cr.height()
        )

    def update_settings(self, config: dict):
        font_family = config.get("font_family")
        font_size = config.get("font_size")
        if font_family or font_size:
            font = self.font()
            if font_family:
                font.setFamily(font_family)
            if font_size:
                font.setPointSize(font_size)
            self.setFont(font)

        word_wrap = config.get("word_wrap")
        if word_wrap is not None:
            self.setWordWrapMode(QTextOption.WordWrap if word_wrap else QTextOption.NoWrap)

        tab_width = config.get("tab_width")
        if tab_width is not None:
            font = self.font()
            self.setTabStopDistance(font.horizontalAdvance("0") * tab_width)

        line_spacing = config.get("line_spacing")
        if line_spacing is not None:
            block = self.document().begin()
            while block.isValid():
                fmt = block.blockFormat()
                fmt.setLineHeight(line_spacing * 100, QTextFormat.LineDistancePercentage)
                block = block.next()

        self._update_line_number_area()

    def _draw_line_numbers(self, event):
        show = _cfg.get("editor.show_line_numbers", True)
        if not show or self.toPlainText() == "":
            return

        is_dark = _cfg.get("theme", "light") == "dark"
        w = self._line_number_area.width()
        line_font = QFont(self.font())
        line_font.setPointSize(max(8, self.font().pointSize() - 1))
        fm = QFontMetrics(line_font)
        line_height = fm.height()

        block_count = self.document().blockCount()
        cursor_block = self.textCursor().blockNumber()
        scroll_top = self.verticalScrollBar().value()
        viewport_height = self.viewport().height()

        first_visible = max(0, int(scroll_top / max(1, line_height)) - 1)
        last_visible = min(block_count, int((scroll_top + viewport_height) / max(1, line_height)) + 2)

        if is_dark:
            line_bg = QColor("#2a2a3c")
            line_bg_current = QColor("#3a3a5c")
            num_color_current = QColor("#89b4fa")
            num_color = QColor("#a6adc8")
        else:
            line_bg = QColor("#f5f6f8")
            line_bg_current = QColor("#e8f0fe")
            num_color_current = QColor("#1565c0")
            num_color = QColor("#555555")

        p = QPainter(self._line_number_area)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            p.fillRect(event.rect(), line_bg)

            for i in range(first_visible, last_visible):
                block = self.document().findBlockByNumber(i)
                if not block.isValid():
                    continue
                y_pos = int(block.layout().position().y() - scroll_top)
                if y_pos + line_height < 0 or y_pos > viewport_height:
                    continue

                num_str = str(i + 1)
                is_current = (i == cursor_block)

                if is_current:
                    p.fillRect(0, y_pos, w, line_height, line_bg_current)
                    p.setPen(QPen(num_color_current, 2))
                else:
                    p.setPen(QPen(num_color, 1))

                num_w = fm.horizontalAdvance(num_str)
                p.drawText(
                    w - 10 - num_w, y_pos,
                    num_w, line_height,
                    Qt.AlignRight | Qt.AlignVCenter,
                    num_str,
                )
        finally:
            p.end()

    def _highlight_current_line(self):
        extra = QTextEdit.ExtraSelection()
        extra.format.setBackground(self._current_line_bg)
        extra.format.setProperty(QTextFormat.FullWidthSelection, True)
        extra.cursor = self.textCursor()
        extra.cursor.clearSelection()
        self.setExtraSelections([extra])

    def _insert_image(self, filepath: str):
        cache_dir = Path.home() / ".wemark2" / "paste_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dest = cache_dir / f"img_{ts}.png"
        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            pixmap.save(str(dest), "PNG")
        else:
            shutil.copy2(filepath, dest)
        cursor = self.textCursor()
        cursor.insertText(f"![]({dest})\n")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and _is_image_file(url.toLocalFile()):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and _is_image_file(url.toLocalFile()):
                    self._insert_image(url.toLocalFile())
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def _line_number_at(self, y: int) -> int:
        margin = self.viewportMargins().left()
        if margin <= 0:
            return -1
        scroll_top = self.verticalScrollBar().value()
        for i in range(self.document().blockCount()):
            block = self.document().findBlockByNumber(i)
            if not block.isValid():
                continue
            y_pos = int(block.layout().position().y() - scroll_top)
            if abs(y_pos - y) < 20:
                return i
        return -1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            margin = self.viewportMargins().left()
            if pos.x() < margin:
                block_num = self._line_number_at(pos.y() - self.viewport().pos().y())
                if block_num >= 0:
                    cursor = QTextCursor(self.document().findBlockByNumber(block_num))
                    cursor.movePosition(QTextCursor.StartOfBlock)
                    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)
                    self._line_drag_anchor = block_num
                    return
        self._line_drag_anchor = -1
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._line_drag_anchor >= 0:
            pos = event.position().toPoint()
            margin = self.viewportMargins().left()
            if pos.x() < margin:
                block_num = self._line_number_at(pos.y() - self.viewport().pos().y())
                if block_num >= 0:
                    start = min(self._line_drag_anchor, block_num)
                    end = max(self._line_drag_anchor, block_num)
                    cursor = QTextCursor(self.document())
                    start_block = self.document().findBlockByNumber(start)
                    end_block = self.document().findBlockByNumber(end)
                    cursor.setPosition(start_block.position())
                    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    cursor.setPosition(end_block.position(), QTextCursor.KeepAnchor)
                    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)
                    return
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.toPlainText() == "":
            p = QPainter(self.viewport())
            try:
                p.setPen(QColor(180, 180, 190, 80))
                font = self.font()
                font.setPointSize(15)
                p.setFont(font)
                rect = self.viewport().rect().adjusted(60, 28, -40, -24)
                p.drawText(rect, Qt.TextWordWrap, tr("editor_placeholder"))
            finally:
                p.end()
            if self._line_number_width() == 0:
                return

        if self._focus_mode:
            is_dark = _cfg.get("theme", "light") == "dark"
            block_count = self.document().blockCount()
            cursor_block = self.textCursor().blockNumber()
            if block_count > 1:
                viewport_height = self.viewport().height()
                scroll_top = self.verticalScrollBar().value()
                line_height = QFontMetrics(self.font()).height()
                focus_alpha = _cfg.get("typewriter.focus_opacity", 160)
                overlay = QColor(255, 255, 255, focus_alpha) if not is_dark else QColor(0, 0, 0, focus_alpha)
                first_visible = max(0, int(scroll_top / max(1, line_height)) - 1)
                last_visible = min(block_count, int((scroll_top + viewport_height) / max(1, line_height)) + 2)
                p = QPainter(self.viewport())
                try:
                    p.setPen(Qt.NoPen)
                    for i in range(first_visible, last_visible):
                        block = self.document().findBlockByNumber(i)
                        if not block.isValid():
                            continue
                        if i == cursor_block:
                            continue
                        y = int(block.layout().position().y() - scroll_top)
                        p.fillRect(0, y, self.viewport().width(), line_height, overlay)
                finally:
                    p.end()

    _SNIPPETS = sorted([
        ("-->", "→"),
        ("==>", "⇒"),
        ("->>", "↠"),
        ("...", "…"),
        ("!=", "≠"),
        ("<=", "≤"),
        (">=", "≥"),
        ("+-", "±"),
        ("<<", "«"),
        (">>", "»"),
        ("(tm)", "™"),
        ("(c)", "©"),
        ("(r)", "®"),
    ], key=lambda x: -len(x[0]))

    @staticmethod
    def _check_snippet(text: str):
        for trigger, result in Editor._SNIPPETS:
            if text.endswith(trigger):
                return (trigger, result)
        return None

    def _show_slash_command_menu(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock)
        block_text = cursor.block().text()
        line_so_far = self.textCursor().block().text()[:self.textCursor().positionInBlock()]
        line_start = line_so_far[:line_so_far.rfind("/")] if "/" in line_so_far else ""
        if line_start.strip():
            return
        cursor_at = self.textCursor()
        cr = self.cursorRect(cursor_at)
        global_pos = self.viewport().mapToGlobal(cr.bottomLeft())
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 4px; font-size: 13px; }"
            "QMenu::item:selected { background: #e8f0fe; color: #1a73e8; }"
        )
        actions = [
            ("H1  一级标题", lambda: self._replace_slash("# ")),
            ("H2  二级标题", lambda: self._replace_slash("## ")),
            ("H3  三级标题", lambda: self._replace_slash("### ")),
            ("", None),
            ("-  无序列表", lambda: self._replace_slash("- ")),
            ("1.  有序列表", lambda: self._replace_slash("1. ")),
            (">  引用", lambda: self._replace_slash("> ")),
            ("```  代码块", lambda: self._replace_slash("```\n\n```") or self._move_cursor_up(1)),
            ("---  分割线", lambda: self._replace_slash("\n---\n")),
            ("", None),
            ("🔗  链接", lambda: self._replace_slash("") or self.apply_link()),
            ("🖼  图片", lambda: self._replace_slash("") or self.apply_image()),
            ("⊞  表格", lambda: self._replace_slash("") or self.apply_table()),
        ]
        for label, slot in actions:
            if not label:
                menu.addSeparator()
                continue
            a = menu.addAction(label)
            if slot:
                a.triggered.connect(slot)
        menu.exec(global_pos)

    def _replace_slash(self, text: str):
        cursor = self.textCursor()
        pos = cursor.positionInBlock()
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, pos)
        sel = cursor.selectedText()
        slash_pos = sel.rfind("/")
        if slash_pos >= 0:
            cursor.setPosition(cursor.selectionStart() + slash_pos)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
            cursor.removeSelectedText()
            cursor.insertText(text)
            self.setTextCursor(cursor)

    def _move_cursor_up(self, n: int):
        cursor = self.textCursor()
        for _ in range(n):
            cursor.movePosition(QTextCursor.Up)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        if modifiers == Qt.ControlModifier:
            if key == Qt.Key_B:
                self.apply_bold(); return
            elif key == Qt.Key_I:
                self.apply_italic(); return
            elif key == Qt.Key_D:
                self.duplicate_line(); return
            elif key == Qt.Key_K:
                self.apply_code_block(); return
            elif key == Qt.Key_J:
                self._toggle_focus_mode(); return
            elif key == Qt.Key_L:
                self._toggle_typewriter_scroll(); return
        elif modifiers == (Qt.ControlModifier | Qt.ShiftModifier):
            if key == Qt.Key_K:
                self.apply_link(); return
            elif key == Qt.Key_C:
                self.apply_code(); return
            elif key == Qt.Key_S:
                self.apply_strikethrough(); return
        elif modifiers == Qt.AltModifier:
            if key == Qt.Key_Up:
                self.move_line_up(); return
            elif key == Qt.Key_Down:
                self.move_line_down(); return

        key_text = event.text()

        if key_text == "/":
            cursor = self.textCursor()
            block_start = cursor.block().text()[:cursor.positionInBlock() - 1]
            if not block_start.strip():
                super().keyPressEvent(event)
                self._show_slash_command_menu()
                return

        if key_text == "[" and not (modifiers & Qt.ControlModifier):
            prev_char = ""
            c = self.textCursor()
            if c.positionInBlock() > 0:
                tc = QTextCursor(c)
                tc.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
                prev_char = tc.selectedText()
            if prev_char == "!":
                path, _ = QFileDialog.getOpenFileName(
                    self.window(), tr("insert_image"), "",
                    f"Images (*{' *'.join(_IMAGE_EXTS)});;All Files (*)")
                if path:
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, 1)
                    cursor.removeSelectedText()
                    self._insert_image(path)
                return

        if key_text in self._auto_pairs:
            self._typing = True
            cursor = self.textCursor()
            if cursor.hasSelection():
                sel = cursor.selectedText()
                cursor.insertText(key_text + sel + self._auto_pairs[key_text])
            else:
                next_char = ""
                if cursor.position() < len(self.toPlainText()):
                    c = QTextCursor(cursor)
                    c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                    next_char = c.selectedText()
                if next_char == self._auto_pairs[key_text]:
                    cursor.movePosition(QTextCursor.Right)
                    self.setTextCursor(cursor)
                else:
                    cursor.insertText(key_text + self._auto_pairs[key_text])
                    cursor.setPosition(cursor.position() - len(self._auto_pairs[key_text]))
                    self.setTextCursor(cursor)
            self._typing = False
            return

        if key == Qt.Key_Tab:
            self._indent()
            return
        if key == Qt.Key_Backtab:
            self._unindent()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._smart_return(event)
            return

        self._typing = True
        super().keyPressEvent(event)
        self._typing = False

        if key_text and key_text.isprintable() and not (modifiers & (Qt.ControlModifier | Qt.AltModifier)):
            self._last_typed += key_text
            self._last_typed = self._last_typed[-6:]
            result = self._check_snippet(self._last_typed)
            if result:
                trigger, replacement = result
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(trigger))
                cursor.removeSelectedText()
                cursor.insertText(replacement)
                self.setTextCursor(cursor)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if image:
                cache_dir = Path.home() / ".wemark2" / "paste_cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filepath = cache_dir / f"paste_{ts}.png"
                image.save(str(filepath), "PNG")
                cursor = self.textCursor()
                cursor.insertText(f"![]({filepath})\n")
                return
        if source.hasText():
            text = source.text().strip()
            url_re = re.compile(
                r'^https?://[^\s]+$', re.I
            )
            if url_re.match(text):
                cursor = self.textCursor()
                if cursor.hasSelection():
                    sel = cursor.selectedText()
                    cursor.insertText(f"[{sel}]({text})")
                    return
        super().insertFromMimeData(source)

    def _indent(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            c = QTextCursor(self.document())
            c.setPosition(start)
            sb = c.block().blockNumber()
            c.setPosition(end)
            eb = c.block().blockNumber()
            if c.atBlockStart() and eb > sb:
                eb -= 1
            cursor.beginEditBlock()
            for i in range(sb, eb + 1):
                block = self.document().findBlockByNumber(i)
                tc = QTextCursor(block)
                tc.movePosition(QTextCursor.StartOfBlock)
                tc.insertText("    ")
            cursor.endEditBlock()
        else:
            cursor.insertText("    ")

    def _unindent(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            c = QTextCursor(self.document())
            c.setPosition(start)
            sb = c.block().blockNumber()
            c.setPosition(end)
            eb = c.block().blockNumber()
            if c.atBlockStart() and eb > sb:
                eb -= 1
            cursor.beginEditBlock()
            for i in range(sb, eb + 1):
                block = self.document().findBlockByNumber(i)
                text = block.text()
                for prefix in ("    ", "\t"):
                    if text.startswith(prefix):
                        tc = QTextCursor(block)
                        tc.movePosition(QTextCursor.StartOfBlock)
                        tc.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(prefix))
                        tc.removeSelectedText()
                        break
            cursor.endEditBlock()
        else:
            block = cursor.block()
            text = block.text()
            for prefix in ("    ", "\t"):
                if text.startswith(prefix):
                    tc = QTextCursor(block)
                    tc.movePosition(QTextCursor.StartOfBlock)
                    tc.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(prefix))
                    tc.removeSelectedText()
                    break

    def _smart_return(self, event):
        cursor = self.textCursor()
        line = cursor.block().text()[:cursor.positionInBlock()]

        for prefix in ("- ", "* ", "+ "):
            if line.lstrip().startswith(prefix):
                indent = line[:line.find(prefix)]
                if line.strip() == prefix.strip():
                    cursor.select(QTextCursor.LineUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deletePreviousChar()
                else:
                    cursor.insertText("\n" + indent + prefix)
                return

        om = re.match(r"^(\s*)(\d+)\.\s?(.*)", line)
        if om:
            indent, num, rest = om.group(1), om.group(2), om.group(3)
            if not rest:
                cursor.select(QTextCursor.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()
            else:
                cursor.insertText(f"\n{indent}{int(num) + 1}. ")
            return

        if line.lstrip().startswith("> ") or line.strip() == ">":
            indent = line[:len(line) - len(line.lstrip())]
            if line.strip() == ">":
                cursor.select(QTextCursor.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()
            else:
                cursor.insertText(f"\n{indent}> ")
            return

        super().keyPressEvent(event)

    def scroll_to_line(self, line: int):
        block = self.document().findBlockByNumber(line - 1)
        if block.isValid():
            cursor = QTextCursor(block)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

    def scroll_to_percent(self, pct: float):
        sb = self.verticalScrollBar()
        sb.setValue(int(pct * sb.maximum()))

    def find_text(self, text: str, case_sensitive=False) -> bool:
        return self.find_text_ext(text, case_sensitive=case_sensitive)

    def find_text_ext(self, text: str, case_sensitive=False, whole_word=False, regex=False) -> bool:
        if regex:
            try:
                flags = 0
                if not case_sensitive:
                    flags = re.IGNORECASE
                pattern = re.compile(text, flags)
                content = self.toPlainText()
                cursor = self.textCursor()
                start_pos = cursor.selectionStart() if cursor.hasSelection() else cursor.position()
                search_start = start_pos if start_pos < len(content) else 0
                remainder = content[search_start:]
                m = pattern.search(remainder)
                if m:
                    abs_pos = search_start + m.start()
                    cursor.setPosition(abs_pos)
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, m.end() - m.start())
                    self.setTextCursor(cursor)
                    return True
                m = pattern.search(content)
                if m:
                    cursor.setPosition(m.start())
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, m.end() - m.start())
                    self.setTextCursor(cursor)
                    return True
                return False
            except re.error:
                return False

        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if whole_word:
            flags |= QTextDocument.FindFlag.FindWholeWords
        cursor = self.textCursor()
        found = self.document().find(text, cursor, flags)
        if not found.isNull():
            self.setTextCursor(found)
            return True
        start = QTextCursor(self.document())
        start.movePosition(QTextCursor.Start)
        found = self.document().find(text, start, flags)
        if not found.isNull():
            self.setTextCursor(found)
            return True
        return False

    def find_replace_one(self, find_text: str, replace_text: str, case_sensitive=False, whole_word=False, regex=False) -> bool:
        if self.find_text_ext(find_text, case_sensitive=case_sensitive, whole_word=whole_word, regex=regex):
            self.textCursor().insertText(replace_text)
            return True
        return False

    def find_replace_all(self, find_text: str, replace_text: str, case_sensitive=False, whole_word=False, regex=False) -> int:
        if regex:
            try:
                flags = 0
                if not case_sensitive:
                    flags = re.IGNORECASE
                text = self.toPlainText()
                pattern = re.compile(find_text, flags)
                new_text, count = pattern.subn(replace_text.replace("\\n", "\n").replace("\\t", "\t"), text)
                if count > 0:
                    cursor = self.textCursor()
                    cursor.beginEditBlock()
                    cursor.select(QTextCursor.Document)
                    cursor.insertText(new_text)
                    cursor.endEditBlock()
                return count
            except re.error:
                return 0

        text = self.toPlainText()
        if case_sensitive:
            count = text.count(find_text)
        else:
            count = text.lower().count(find_text.lower())
        if whole_word:
            flags = 0 if case_sensitive else re.IGNORECASE
            count = len(re.findall(r'\b' + re.escape(find_text) + r'\b', text, flags))
        if count > 0:
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.select(QTextCursor.Document)
            if whole_word:
                flags = 0 if case_sensitive else re.IGNORECASE
                result = re.sub(r'\b' + re.escape(find_text) + r'\b', replace_text, text, flags=flags)
            elif case_sensitive:
                result = text.replace(find_text, replace_text)
            else:
                result = re.sub(re.escape(find_text), replace_text, text, flags=re.IGNORECASE)
            cursor.insertText(result)
            cursor.endEditBlock()
        return count

    def apply_bold(self): self._wrap("**")
    def apply_italic(self): self._wrap("*")
    def apply_strikethrough(self): self._wrap("~~")
    def apply_code(self): self._wrap("`")

    def apply_heading(self, level=1):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.insertText("#" * level + " ")

    def apply_quote(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText().replace("\u2029", "\n")
            lines = text.split("\n")
            cursor.insertText("\n".join("> " + l for l in lines))
        else:
            cursor.insertText("> ")

    def apply_list(self, ordered=False):
        self.textCursor().insertText("\n" + ("1. " if ordered else "- "))

    def apply_link(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.insertText(f"[{cursor.selectedText()}](url)")
        else:
            cursor.insertText(f"[{tr('link_text')}](url)")

    def apply_table(self):
        c1, c2, c3 = tr("table_col1"), tr("table_col2"), tr("table_col3")
        self.textCursor().insertText(f"\n| {c1} | {c2} | {c3} |\n| --- | --- | --- |\n|  |  |  |\n")

    def apply_hr(self):
        self.textCursor().insertText("\n---\n")

    def format_markdown(self):
        text = self.toPlainText()
        if not text:
            return
        lines = text.split("\n")
        result = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                result.append(line)
                continue
            if not in_code_block:
                line = line.rstrip()
                if line == "" and result and result[-1] == "":
                    continue
            result.append(line)
        while result and result[-1] == "":
            result.pop()
        text = "\n".join(result) + "\n"

        table_lines = []
        output = []
        for line in text.split("\n"):
            if "|" in line and "--" in line and line.strip().startswith("|"):
                table_lines.append(line)
            elif table_lines and ("|" in line):
                table_lines.append(line)
            else:
                if table_lines:
                    output.extend(self._align_table(table_lines))
                    table_lines = []
                output.append(line)
        if table_lines:
            output.extend(self._align_table(table_lines))
        text = "\n".join(output)

        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.Document)
        cursor.insertText(text)
        cursor.endEditBlock()

    @staticmethod
    def _align_table(rows):
        if not rows:
            return rows
        parts = [col.strip() for col in rows[0].split("|")[1:-1]]
        widths = [len(p) for p in parts]
        for row in rows[1:]:
            cols = [c.strip() for c in row.split("|")[1:-1]]
            for i, c in enumerate(cols):
                if i < len(widths):
                    widths[i] = max(widths[i], len(c))
        out = []
        for row in rows:
            cols = [c.strip() for c in row.split("|")]
            formatted = []
            for i, c in enumerate(cols):
                if i == 0 or i == len(cols) - 1:
                    formatted.append(c)
                elif i - 1 < len(widths):
                    w = widths[i - 1]
                    if ":" in c.replace("-", "").strip():
                        formatted.append(" " + "-" * max(w, 3) + " ")
                    else:
                        formatted.append(" " + c.ljust(w) + " ")
            out.append("|".join(formatted))
        return out

    def _wrap(self, marker: str):
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"{marker}{text}{marker}")
        else:
            cursor.insertText(marker * 2)
            cursor.setPosition(cursor.position() - len(marker))
            self.setTextCursor(cursor)

    def apply_code_block(self, language=""):
        cursor = self.textCursor()
        line = cursor.block().text()
        indent = re.match(r"^(\s*)", line).group(1) if line else ""
        if cursor.hasSelection():
            text = cursor.selectedText().replace("\u2029", "\n")
            cursor.insertText(f"{indent}```{language}\n{text}\n{indent}```")
        else:
            cursor.insertText(f"{indent}```{language}\n\n{indent}```")
            cursor.movePosition(QTextCursor.Up)
            self.setTextCursor(cursor)

    def apply_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window(), tr("insert_image"), "",
            f"Images (*{' *'.join(_IMAGE_EXTS)});;All Files (*)")
        if path:
            self._insert_image(path)

    def duplicate_line(self):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if cursor.hasSelection():
            text = cursor.selectedText().replace("\u2029", "\n")
            cursor.clearSelection()
            cursor.insertText("\n" + text)
        else:
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            text = cursor.selectedText()
            cursor.clearSelection()
            cursor.insertText("\n" + text)
        cursor.endEditBlock()

    def move_line_up(self):
        cursor = self.textCursor()
        block = cursor.block()
        prev = block.previous()
        if not prev.isValid():
            return
        block_num = block.blockNumber()
        prev_num = prev.blockNumber()
        cursor.beginEditBlock()
        block_text = self.document().findBlockByNumber(block_num).text()
        prev_text = self.document().findBlockByNumber(prev_num).text()
        tc = QTextCursor(self.document().findBlockByNumber(prev_num))
        tc.movePosition(QTextCursor.StartOfBlock)
        tc.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        tc.insertText(block_text)
        tc = QTextCursor(self.document().findBlockByNumber(block_num))
        tc.movePosition(QTextCursor.StartOfBlock)
        tc.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        tc.insertText(prev_text)
        cursor.endEditBlock()
        cursor.movePosition(QTextCursor.Up)
        self.setTextCursor(cursor)

    def move_line_down(self):
        cursor = self.textCursor()
        block = cursor.block()
        nxt = block.next()
        if not nxt.isValid():
            return
        block_num = block.blockNumber()
        next_num = nxt.blockNumber()
        cursor.beginEditBlock()
        block_text = self.document().findBlockByNumber(block_num).text()
        next_text = self.document().findBlockByNumber(next_num).text()
        tc = QTextCursor(self.document().findBlockByNumber(block_num))
        tc.movePosition(QTextCursor.StartOfBlock)
        tc.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        tc.insertText(next_text)
        tc = QTextCursor(self.document().findBlockByNumber(next_num))
        tc.movePosition(QTextCursor.StartOfBlock)
        tc.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        tc.insertText(block_text)
        cursor.endEditBlock()
        cursor.movePosition(QTextCursor.Down)
        self.setTextCursor(cursor)

    def zoom_in(self):
        font = self.font()
        font.setPointSize(max(8, font.pointSize() + 1))
        self.setFont(font)
        self._update_line_number_area()

    def zoom_out(self):
        font = self.font()
        font.setPointSize(max(8, font.pointSize() - 1))
        self.setFont(font)
        self._update_line_number_area()

    def reset_zoom(self):
        font = self.font()
        font.setPointSize(16)
        self.setFont(font)
        self._update_line_number_area()

    def _toggle_focus_mode(self):
        self._focus_mode = not self._focus_mode
        self.viewport().update()
        self.mode_changed.emit()

    def _toggle_typewriter_scroll(self):
        self._typewriter_scroll = not self._typewriter_scroll
        if self._typewriter_scroll:
            self._center_cursor()
        self.mode_changed.emit()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        fmt_menu = menu.addMenu(tr("ctx_markdown"))
        fmt_actions = [
            (tr("ctx_bold"), lambda: self.apply_bold()),
            (tr("ctx_italic"), lambda: self.apply_italic()),
            (tr("ctx_strikethrough"), lambda: self.apply_strikethrough()),
            (tr("ctx_code"), lambda: self.apply_code()),
            (tr("ctx_link"), lambda: self.apply_link()),
        ]
        for label, slot in fmt_actions:
            a = fmt_menu.addAction(label)
            a.triggered.connect(slot)
        block_menu = menu.addMenu(tr("ctx_block"))
        block_actions = [
            (tr("ctx_heading1"), lambda: self.apply_heading(1)),
            (tr("ctx_heading2"), lambda: self.apply_heading(2)),
            (tr("ctx_heading3"), lambda: self.apply_heading(3)),
            (tr("ctx_quote"), lambda: self.apply_quote()),
            (tr("ctx_ulist"), lambda: self.apply_list(False)),
            (tr("ctx_olist"), lambda: self.apply_list(True)),
            (tr("ctx_codeblock"), lambda: self.apply_code_block()),
            (tr("ctx_table"), lambda: self.apply_table()),
            (tr("ctx_image"), lambda: self.apply_image()),
            (tr("ctx_hr"), lambda: self.apply_hr()),
        ]
        for label, slot in block_actions:
            a = block_menu.addAction(label)
            a.triggered.connect(slot)
        menu.addSeparator()
        line_menu = menu.addMenu(tr("ctx_line_ops"))
        line_actions = [
            (tr("ctx_duplicate"), lambda: self.duplicate_line()),
            (tr("ctx_move_up"), lambda: self.move_line_up()),
            (tr("ctx_move_down"), lambda: self.move_line_down()),
        ]
        for label, slot in line_actions:
            a = line_menu.addAction(label)
            a.triggered.connect(slot)
        menu.addSeparator()
        ai_menu = menu.addMenu(tr("ctx_ai_write"))
        cursor = self.textCursor()
        has_selection = cursor.hasSelection()
        selection = cursor.selectedText().replace("\u2029", "\n")[:80] + ("…" if len(cursor.selectedText()) > 80 else "") if has_selection else ""
        ai_actions = [
            (tr("ctx_ai_continue") + (f" 「{selection}」" if selection else ""), "continue_writing"),
            (tr("ctx_ai_polish") + (f" 「{selection}」" if selection else " 全文"), "polish"),
            (tr("ctx_ai_translate") + (f" 「{selection}」" if selection else " 全文"), "translate"),
            (tr("ctx_ai_summarize") + (" 全文" if not has_selection else " 选中"), "summarize"),
        ]
        for label, action in ai_actions:
            a = ai_menu.addAction(label)
            a.triggered.connect(lambda checked=False, act=action: self.ai_action_requested.emit(act, self.textCursor().selectedText().replace("\u2029", "\n") if self.textCursor().hasSelection() else ""))
        menu.addSeparator()
        menu.addAction(tr("ctx_slash_cmd"), lambda: self._show_slash_command_menu())
        menu.exec(event.globalPos())

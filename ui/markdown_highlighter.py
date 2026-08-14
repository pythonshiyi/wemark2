import re

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


def _fmt(color=None, bold=False, italic=False, bg=None) -> QTextCharFormat:
    f = QTextCharFormat()
    if color: f.setForeground(QColor(color))
    if bold: f.setFontWeight(QFont.Bold)
    if italic: f.setFontItalic(True)
    if bg: f.setBackground(QColor(bg))
    return f


CODE_BLOCK = 1

class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        self._hdr_pats = []
        self._hdr_fmts = []
        for i in range(1, 7):
            self._hdr_pats.append(re.compile(r"^" + "#" * i + r"\s+.*", re.MULTILINE))
            self._hdr_fmts.append(_fmt("#1a73e8", bold=True))

        self._bold_re = re.compile(r"\*\*(.+?)\*\*")
        self._bold_fmt = _fmt("#333333", bold=True)

        self._italic_re = re.compile(r"(?<!\*)\*(?!\*)(.+?)\*(?!\*)")
        self._italic_fmt = _fmt("#666666", italic=True)

        self._strike_re = re.compile(r"~~(.+?)~~")
        self._strike_fmt = _fmt("#999999", italic=True)

        self._code_re = re.compile(r"`([^`\n]+)`")
        self._code_fmt = _fmt("#d32f2f", bg="#f0f0f0")

        self._link_re = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
        self._link_fmt = _fmt("#1a73e8")

        self._img_re = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
        self._img_fmt = _fmt("#4caf50")

        self._bq_re = re.compile(r"^>{1,4}\s.*$", re.MULTILINE)
        self._bq_fmt = _fmt("#1a73e8")

        self._ul_re = re.compile(r"^\s*[-*+]\s", re.MULTILINE)
        self._ol_re = re.compile(r"^\s*\d+\.\s", re.MULTILINE)
        self._list_fmt = _fmt("#1a73e8", bold=True)

        self._hr_re = re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE)
        self._hr_fmt = _fmt("#cccccc")

        self._block_fmt = _fmt("#d32f2f", bg="#f0f0f0")

    def highlightBlock(self, text: str):
        prev = self.previousBlockState()

        if prev == CODE_BLOCK:
            self.setFormat(0, len(text), self._block_fmt)
            self.setCurrentBlockState(0 if text.strip().startswith("```") else CODE_BLOCK)
            return

        stripped = text.strip()
        if stripped.startswith("```"):
            self.setFormat(0, len(text), self._block_fmt)
            self.setCurrentBlockState(CODE_BLOCK if text.count("```") < 2 else 0)
            return

        self.setCurrentBlockState(0)

        for i, pat in enumerate(self._hdr_pats):
            for m in pat.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), self._hdr_fmts[i])

        for m in self._bold_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._bold_fmt)
        for m in self._italic_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._italic_fmt)
        for m in self._strike_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._strike_fmt)
        for m in self._code_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._code_fmt)
        for m in self._img_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._img_fmt)
        for m in self._link_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._link_fmt)
        for m in self._bq_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._bq_fmt)
        for m in self._ul_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._list_fmt)
        for m in self._ol_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._list_fmt)
        for m in self._hr_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._hr_fmt)

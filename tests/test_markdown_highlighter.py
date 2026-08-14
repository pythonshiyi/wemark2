from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument, QFont

from ui.markdown_highlighter import MarkdownHighlighter, _fmt, CODE_BLOCK


class TestFmt:
    def test_fmt_color_only(self):
        f = _fmt(color="#ff0000")
        assert f.foreground().color().name() == "#ff0000"

    def test_fmt_bold(self):
        f = _fmt(bold=True)
        assert f.fontWeight() == QFont.Bold

    def test_fmt_italic(self):
        f = _fmt(italic=True)
        assert f.fontItalic() is True

    def test_fmt_background(self):
        f = _fmt(bg="#f0f0f0")
        assert f.background().color().name() == "#f0f0f0"

    def test_fmt_all_properties(self):
        f = _fmt(color="#1a73e8", bold=True, italic=True, bg="#ffffff")
        assert f.foreground().color().name() == "#1a73e8"
        assert f.fontWeight() == QFont.Bold
        assert f.fontItalic() is True
        assert f.background().color().name() == "#ffffff"


class TestCodeBlockConstant:
    def test_code_block_value(self):
        assert CODE_BLOCK == 1


class TestHighlighterCreation:
    def test_highlighter_creation(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("hello")
        hl = MarkdownHighlighter(doc)
        assert hl is not None
        assert hl.document() == doc


class TestHighlighterHeadings:
    def test_highlight_h1(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("# Heading 1")
        hl = MarkdownHighlighter(doc)
        fmt = hl._hdr_fmts[0]
        assert fmt.foreground().color().name() == "#1a73e8"
        assert fmt.fontWeight() == QFont.Bold

    def test_highlight_h2(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("## Heading 2")
        hl = MarkdownHighlighter(doc)
        fmt = hl._hdr_fmts[1]
        assert fmt.foreground().color().name() == "#1a73e8"

    def test_heading_patterns_initialized(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        assert len(hl._hdr_pats) == 6
        assert len(hl._hdr_fmts) == 6


class TestHighlighterBold:
    def test_highlight_bold(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("**bold** text")
        hl = MarkdownHighlighter(doc)
        fmt = hl._bold_fmt
        assert fmt.foreground().color().name() == "#333333"
        assert fmt.fontWeight() == QFont.Bold

    def test_bold_regex_pattern(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        assert hl._bold_re.pattern == r"\*\*(.+?)\*\*"


class TestHighlighterItalic:
    def test_highlight_italic(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("*italic* text")
        hl = MarkdownHighlighter(doc)
        fmt = hl._italic_fmt
        assert fmt.foreground().color().name() == "#666666"
        assert fmt.fontItalic() is True


class TestHighlighterCode:
    def test_highlight_inline_code(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("`code` here")
        hl = MarkdownHighlighter(doc)
        fmt = hl._code_fmt
        assert fmt.foreground().color().name() == "#d32f2f"

    def test_code_block_format(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        fmt = hl._block_fmt
        assert fmt.foreground().color().name() == "#d32f2f"


class TestHighlighterLink:
    def test_highlight_link(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("[text](url)")
        hl = MarkdownHighlighter(doc)
        fmt = hl._link_fmt
        assert fmt.foreground().color().name() == "#1a73e8"

    def test_link_regex(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        assert hl._link_re.pattern == r"\[([^\]]*)\]\(([^)]*)\)"


class TestHighlighterImage:
    def test_highlight_image(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("![alt](img.png)")
        hl = MarkdownHighlighter(doc)
        fmt = hl._img_fmt
        assert fmt.foreground().color().name() == "#4caf50"


class TestHighlighterBlockquote:
    def test_highlight_blockquote(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("> quoted text")
        hl = MarkdownHighlighter(doc)
        fmt = hl._bq_fmt
        assert fmt.foreground().color().name() == "#1a73e8"

    def test_blockquote_regex(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        assert hl._bq_re.pattern == r"^>{1,4}\s.*$"


class TestHighlighterList:
    def test_highlight_unordered_list(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("- item")
        hl = MarkdownHighlighter(doc)
        fmt = hl._list_fmt
        assert fmt.foreground().color().name() == "#1a73e8"
        assert fmt.fontWeight() == QFont.Bold

    def test_list_regex_patterns(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        assert hl._ul_re.pattern == r"^\s*[-*+]\s"

    def test_ordered_list_regex(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        assert hl._ol_re.pattern == r"^\s*\d+\.\s"


class TestHighlighterHr:
    def test_highlight_hr(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("---")
        hl = MarkdownHighlighter(doc)
        fmt = hl._hr_fmt
        assert fmt.foreground().color().name() == "#cccccc"

    def test_hr_regex(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        assert hl._hr_re.pattern == r"^[-*_]{3,}\s*$"


class TestHighlighterStrikethrough:
    def test_highlight_strikethrough(self, qapp):
        doc = QTextDocument()
        doc.setPlainText("~~text~~")
        hl = MarkdownHighlighter(doc)
        fmt = hl._strike_fmt
        assert fmt.foreground().color().name() == "#999999"
        assert fmt.fontItalic() is True


class TestHighlighterCodeBlockState:
    def test_code_block_state_value(self, qapp):
        assert CODE_BLOCK == 1

    def test_code_block_format_used_for_block(self, qapp):
        doc = QTextDocument()
        hl = MarkdownHighlighter(doc)
        assert hl._block_fmt is not None

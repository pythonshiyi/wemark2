from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest

from ui.editor import Editor


class TestEditorSnippets:
    def test_check_snippet_returns_replacement(self):
        assert Editor._check_snippet("-->") == ("-->", "→")
        assert Editor._check_snippet("abc-->") == ("-->", "→")
        assert Editor._check_snippet("==>") == ("==>", "⇒")

    def test_check_snippet_no_match(self):
        assert Editor._check_snippet("hello") is None
        assert Editor._check_snippet("abc") is None
        assert Editor._check_snippet("") is None

    def test_check_snippet_all_entries(self):
        for trigger, result in Editor._SNIPPETS:
            assert Editor._check_snippet(trigger) == (trigger, result)
            assert Editor._check_snippet(" " + trigger) == (trigger, result)

    def test_snippet_expansion_in_document(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        from PySide6.QtTest import QTest
        for ch in "-->":
            QTest.keyClick(editor, ch)
        assert "→" in editor.toPlainText()

    def test_snippet_arrow_replaces_in_document(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        from PySide6.QtTest import QTest
        for ch in "-->":
            QTest.keyClick(editor, ch)
        assert "→" in editor.toPlainText()

    def test_snippet_does_not_fire_within_word(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        from PySide6.QtTest import QTest
        for ch in "abc--":
            QTest.keyClick(editor, ch)
        text = editor.toPlainText()
        assert "—" not in text


class TestEditorFocusMode:
    def test_focus_mode_off_by_default(self, qapp):
        editor = Editor()
        assert editor._focus_mode is False

    def test_toggle_focus_mode(self, qapp):
        editor = Editor()
        editor._toggle_focus_mode()
        assert editor._focus_mode is True
        editor._toggle_focus_mode()
        assert editor._focus_mode is False

    def test_focus_mode_emits_signal(self, qapp):
        editor = Editor()
        signals = []
        editor.mode_changed.connect(lambda: signals.append(1))
        editor._toggle_focus_mode()
        assert len(signals) == 1


class TestEditorTypewriterScroll:
    def test_typewriter_off_by_default(self, qapp):
        editor = Editor()
        assert editor._typewriter_scroll is False

    def test_toggle_typewriter_scroll(self, qapp):
        editor = Editor()
        editor._toggle_typewriter_scroll()
        assert editor._typewriter_scroll is True
        editor._toggle_typewriter_scroll()
        assert editor._typewriter_scroll is False

    def test_typewriter_emits_signal(self, qapp):
        editor = Editor()
        signals = []
        editor.mode_changed.connect(lambda: signals.append(1))
        editor._toggle_typewriter_scroll()
        assert len(signals) == 1


class TestEditorBasics:
    def test_editor_creation(self, qapp):
        editor = Editor()
        assert editor is not None
        assert editor.toPlainText() == ""

    def test_editor_accepts_markdown(self, qapp):
        editor = Editor()
        editor.setPlainText("# Hello\n**bold** text")
        assert editor.toPlainText() == "# Hello\n**bold** text"

    def test_get_markdown_returns_content(self, qapp):
        editor = Editor()
        editor.setPlainText("test content")
        assert editor.get_markdown() == "test content"

    def test_default_font_size(self, qapp):
        editor = Editor()
        assert editor.font().pointSize() > 0

    def test_editor_not_rich_text(self, qapp):
        editor = Editor()
        assert editor.acceptRichText() is False


class TestEditorAutoPair:
    def test_auto_pair_parentheses(self, qapp):
        editor = Editor()
        editor.setFocus()
        editor.setPlainText("")
        cursor = editor.textCursor()
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_ParenLeft)
        assert editor.toPlainText() == "()"

    def test_auto_pair_brackets(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        QTest.keyClick(editor, Qt.Key_BracketLeft)
        assert editor.toPlainText() == "[]"

    def test_auto_pair_braces(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        QTest.keyClick(editor, Qt.Key_BraceLeft)
        assert editor.toPlainText() == "{}"

    def test_auto_pair_quotes(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        QTest.keyClick(editor, Qt.Key_QuoteDbl)
        assert editor.toPlainText() == '""'

    def test_auto_pair_asterisk(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        QTest.keyClick(editor, Qt.Key_Asterisk)
        assert editor.toPlainText() == "**"

    def test_auto_pair_backtick(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        QTest.keyClick(editor, Qt.Key_QuoteLeft)
        assert editor.toPlainText() == "``"

    def test_cursor_inside_auto_pair(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        QTest.keyClick(editor, Qt.Key_ParenLeft)
        cursor = editor.textCursor()
        assert cursor.position() == 1


class TestEditorFormatting:
    def test_apply_bold_no_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.setPosition(3)
        editor.setTextCursor(cursor)
        editor.apply_bold()
        assert editor.toPlainText() == "hel****lo"

    def test_apply_bold_with_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("hello world")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 5)
        editor.setTextCursor(cursor)
        editor.apply_bold()
        assert editor.toPlainText() == "**hello** world"

    def test_apply_italic_with_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("hello world")
        cursor = editor.textCursor()
        cursor.setPosition(0)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 5)
        editor.setTextCursor(cursor)
        editor.apply_italic()
        assert editor.toPlainText() == "*hello* world"

    def test_apply_strikethrough_with_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        editor.apply_strikethrough()
        assert editor.toPlainText() == "~~hello~~"

    def test_apply_code_with_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        editor.apply_code()
        assert editor.toPlainText() == "`hello`"

    def test_apply_heading(self, qapp):
        editor = Editor()
        editor.setPlainText("Title")
        editor.apply_heading(1)
        assert editor.toPlainText() == "# Title"

    def test_apply_heading_level_2(self, qapp):
        editor = Editor()
        editor.setPlainText("Subtitle")
        editor.apply_heading(2)
        assert editor.toPlainText() == "## Subtitle"

    def test_apply_heading_level_3(self, qapp):
        editor = Editor()
        editor.setPlainText("Section")
        editor.apply_heading(3)
        assert editor.toPlainText() == "### Section"


class TestEditorCodeBlock:
    def test_apply_code_block_no_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        editor.apply_code_block()
        text = editor.toPlainText()
        assert "```" in text
        assert text.count("```") == 2

    def test_apply_code_block_with_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("print('hello')")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        editor.apply_code_block("python")
        text = editor.toPlainText()
        assert "```python" in text
        assert "print" in text

    def test_apply_code_block_with_language(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        editor.apply_code_block("javascript")
        assert "```javascript" in editor.toPlainText()

    def test_apply_code_block_cursor_position(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        editor.apply_code_block()
        cursor = editor.textCursor()
        text = editor.toPlainText()
        lines = text.split("\n")
        assert len(lines) >= 2
        assert cursor.block().text() == ""


class TestEditorLists:
    def test_smart_enter_continues_unordered_list(self, qapp):
        editor = Editor()
        editor.setPlainText("- item")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert "- " in editor.toPlainText()

    def test_smart_enter_continues_ordered_list(self, qapp):
        editor = Editor()
        editor.setPlainText("1. item")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert "2. " in editor.toPlainText()

    def test_smart_enter_continues_blockquote(self, qapp):
        editor = Editor()
        editor.setPlainText("> quote")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert "> " in editor.toPlainText()

    def test_smart_enter_ends_empty_ordered_list(self, qapp):
        editor = Editor()
        editor.setPlainText("1. ")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert editor.toPlainText().strip() == ""

    def test_smart_enter_ends_empty_ordered_list_no_trailing_space(self, qapp):
        editor = Editor()
        editor.setPlainText("1.")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert editor.toPlainText().strip() == ""

    def test_smart_enter_ends_empty_blockquote(self, qapp):
        editor = Editor()
        editor.setPlainText("> ")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert editor.toPlainText().strip() == ""

    def test_smart_enter_ends_empty_blockquote_no_trailing_space(self, qapp):
        editor = Editor()
        editor.setPlainText(">")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert editor.toPlainText().strip() == ""

    def test_smart_enter_continues_blockquote(self, qapp):
        editor = Editor()
        editor.setPlainText("> quoted text")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert "> " in editor.toPlainText()

    def test_smart_enter_ends_empty_list_item(self, qapp):
        editor = Editor()
        editor.setPlainText("- ")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Return)
        assert editor.toPlainText().strip() == ""


class TestEditorLineOperations:
    def test_duplicate_line(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2\nline 3")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down)
        editor.setTextCursor(cursor)
        editor.duplicate_line()
        lines = editor.toPlainText().split("\n")
        assert len(lines) == 4

    def test_duplicate_line_no_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("single line")
        editor.duplicate_line()
        lines = editor.toPlainText().split("\n")
        assert len(lines) == 2
        assert lines[0] == "single line"
        assert lines[1] == "single line"

    def test_duplicate_selected_text(self, qapp):
        editor = Editor()
        editor.setPlainText("abc\ndef\nghi")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 2)
        editor.setTextCursor(cursor)
        editor.duplicate_line()
        assert "def" in editor.toPlainText()

    def test_move_line_up(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2\nline 3")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down)
        editor.setTextCursor(cursor)
        editor.move_line_up()
        lines = editor.toPlainText().split("\n")
        assert lines[0] == "line 2"
        assert lines[1] == "line 1"

    def test_move_line_down(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2\nline 3")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)
        editor.move_line_down()
        lines = editor.toPlainText().split("\n")
        assert lines[0] == "line 2"
        assert lines[1] == "line 1"

    def test_move_line_up_at_top(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)
        editor.move_line_up()
        assert editor.toPlainText() == "line 1\nline 2"

    def test_move_line_down_at_bottom(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        editor.move_line_down()
        assert editor.toPlainText() == "line 1\nline 2"


class TestEditorIndent:
    def test_indent_single_line(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        QTest.keyClick(editor, Qt.Key_Tab)
        assert editor.toPlainText() == "    hello"

    def test_unindent_single_line(self, qapp):
        editor = Editor()
        editor.setPlainText("    hello")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Backtab)
        assert editor.toPlainText() == "hello"

    def test_indent_multiple_lines(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2\nline 3")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 2)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Tab)
        lines = editor.toPlainText().split("\n")
        assert lines[0] == "    line 1"
        assert lines[1] == "    line 2"
        assert lines[2] == "line 3"

    def test_unindent_multiple_lines(self, qapp):
        editor = Editor()
        editor.setPlainText("    line 1\n    line 2\nline 3")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 2)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Backtab)
        lines = editor.toPlainText().split("\n")
        assert lines[0] == "line 1"
        assert lines[1] == "line 2"
        assert lines[2] == "line 3"


class TestEditorLink:
    def test_apply_link_with_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("click here")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        editor.apply_link()
        assert editor.toPlainText() == "[click here](url)"

    def test_apply_link_no_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        editor.apply_link()
        assert editor.toPlainText() == "[文本](url)"


class TestEditorTable:
    def test_apply_table(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        editor.apply_table()
        text = editor.toPlainText()
        assert "|" in text
        assert "列1" in text or "---" in text


class TestEditorHr:
    def test_apply_hr(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        editor.apply_hr()
        assert "---" in editor.toPlainText()


class TestEditorScrollAndCursor:
    def test_scroll_to_line(self, qapp):
        editor = Editor()
        lines = "\n".join(f"line {i}" for i in range(50))
        editor.setPlainText(lines)
        editor.scroll_to_line(25)
        cursor = editor.textCursor()
        assert cursor.blockNumber() == 24

    def test_cursor_line_changed_signal(self, qapp):
        editor = Editor()
        signals = []
        editor.cursor_line_changed.connect(lambda l, t: signals.append((l, t)))
        editor.setPlainText("line 1\nline 2\nline 3")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Down)
        editor.setTextCursor(cursor)
        assert len(signals) >= 1
        assert signals[-1][0] == 2

    def test_scroll_changed_signal(self, qapp):
        editor = Editor()
        signals = []
        editor.scroll_changed.connect(lambda v: signals.append(v))
        # Just verify creation
        assert editor.scroll_changed is not None


class TestEditorFindReplace:
    def test_find_text_found(self, qapp):
        editor = Editor()
        editor.setPlainText("hello world")
        assert editor.find_text("world") is True

    def test_find_text_not_found(self, qapp):
        editor = Editor()
        editor.setPlainText("hello world")
        assert editor.find_text("xyz") is False

    def test_find_replace_one(self, qapp):
        editor = Editor()
        editor.setPlainText("hello world")
        editor.find_replace_one("world", "there")
        assert editor.toPlainText() == "hello there"

    def test_find_replace_all(self, qapp):
        editor = Editor()
        editor.setPlainText("a a a")
        count = editor.find_replace_all("a", "b")
        assert count == 3
        assert editor.toPlainText() == "b b b"

    def test_find_case_sensitive(self, qapp):
        editor = Editor()
        editor.setPlainText("Hello hello HELLO")
        assert editor.find_text("hello", case_sensitive=False) is True


class TestEditorQuote:
    def test_apply_quote_with_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        editor.apply_quote()
        assert "> line 1" in editor.toPlainText()
        assert "> line 2" in editor.toPlainText()

    def test_apply_quote_no_selection(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        editor.apply_quote()
        assert editor.toPlainText() == "> "


class TestEditorZoom:
    def test_zoom_increases_font_size(self, qapp):
        editor = Editor()
        initial = editor.font().pointSize()
        editor.zoom_in()
        assert editor.font().pointSize() == initial + 1

    def test_zoom_out_decreases_font_size(self, qapp):
        editor = Editor()
        editor.zoom_in()
        initial = editor.font().pointSize()
        editor.zoom_out()
        assert editor.font().pointSize() == initial - 1

    def test_zoom_reset(self, qapp):
        editor = Editor()
        editor.zoom_in()
        editor.zoom_in()
        editor.reset_zoom()
        assert editor.font().pointSize() == 16


class TestEditorSlashCommand:
    def test_replace_slash_replaces_slash(self, qapp):
        editor = Editor()
        editor.setPlainText("abc/")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        editor._replace_slash("## ")
        text = editor.toPlainText()
        assert "/" not in text
        assert "## " in text

    def test_replace_slash_empty_no_slash_no_change(self, qapp):
        editor = Editor()
        editor.setPlainText("noslash")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        editor._replace_slash("## ")
        assert editor.toPlainText() == "noslash"

    def test_move_cursor_up(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2\nline 3")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Down)
        editor.setTextCursor(cursor)
        editor._move_cursor_up(1)
        c = editor.textCursor()
        assert c.blockNumber() == 0

    def test_slash_not_at_start_does_not_open_menu(self, qapp):
        editor = Editor()
        editor.setPlainText("abc/")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)
        from PySide6.QtTest import QTest
        QTest.keyClick(editor, Qt.Key_Slash)
        # Should just insert / without opening menu
        assert editor.toPlainText() == "abc//"


class TestEditorKeyboardShortcuts:
    def test_ctrl_b_applies_bold(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_B, Qt.ControlModifier)
        assert editor.toPlainText() == "**hello**"

    def test_ctrl_i_applies_italic(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_I, Qt.ControlModifier)
        assert editor.toPlainText() == "*hello*"

    def test_ctrl_k_inserts_code_block(self, qapp):
        editor = Editor()
        editor.setPlainText("")
        QTest.keyClick(editor, Qt.Key_K, Qt.ControlModifier)
        assert "```" in editor.toPlainText()

    def test_ctrl_d_duplicates_line(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_D, Qt.ControlModifier)
        lines = editor.toPlainText().split("\n")
        assert len(lines) == 2
        assert lines[0] == "hello"

    def test_alt_up_moves_line_up(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Down)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Up, Qt.AltModifier)
        lines = editor.toPlainText().split("\n")
        assert lines[0] == "line 2"

    def test_alt_down_moves_line_down(self, qapp):
        editor = Editor()
        editor.setPlainText("line 1\nline 2")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_Down, Qt.AltModifier)
        lines = editor.toPlainText().split("\n")
        assert lines[0] == "line 2"

    def test_ctrl_shift_c_applies_code(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_C, Qt.ControlModifier | Qt.ShiftModifier)
        assert editor.toPlainText() == "`hello`"

    def test_ctrl_shift_s_applies_strikethrough(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_S, Qt.ControlModifier | Qt.ShiftModifier)
        assert editor.toPlainText() == "~~hello~~"

    def test_ctrl_shift_k_applies_link(self, qapp):
        editor = Editor()
        editor.setPlainText("hello")
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        editor.setTextCursor(cursor)
        QTest.keyClick(editor, Qt.Key_K, Qt.ControlModifier | Qt.ShiftModifier)
        assert editor.toPlainText() == "[hello](url)"

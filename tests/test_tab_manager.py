from PySide6.QtCore import Qt

from ui.tab_manager import TabManager, EditorTab


class TestTabManagerCreation:
    def test_tab_manager_creation(self, qapp):
        tm = TabManager()
        assert tm is not None
        assert tm.count() == 0

    def test_add_tab_creates_editor(self, qapp):
        tm = TabManager()
        editor = tm.add_tab()
        assert editor is not None
        assert tm.count() == 1

    def test_add_tab_with_content(self, qapp):
        tm = TabManager()
        editor = tm.add_tab(content="# Hello\nWorld")
        assert editor.get_markdown() == "# Hello\nWorld"
        assert tm.count() == 1

    def test_get_current_editor_returns_none_when_empty(self, qapp):
        tm = TabManager()
        assert tm.get_current_editor() is None

    def test_get_current_editor_after_add(self, qapp):
        tm = TabManager()
        editor = tm.add_tab("Test")
        assert tm.get_current_editor() is editor

    def test_add_multiple_tabs(self, qapp):
        tm = TabManager()
        tm.add_tab("Tab 1")
        tm.add_tab("Tab 2")
        tm.add_tab("Tab 3")
        assert tm.count() == 3

    def test_current_index_starts_at_0(self, qapp):
        tm = TabManager()
        tm.add_tab("First")
        assert tm.current_index() == 0

    def test_current_index_after_multiple_tabs(self, qapp):
        tm = TabManager()
        tm.add_tab("First")
        tm.add_tab("Second")
        assert tm.current_index() == 1

    def test_get_current_tab(self, qapp):
        tm = TabManager()
        editor = tm.add_tab("Test")
        tab = tm.get_current_tab()
        assert tab is not None
        assert tab.editor is editor


class TestEditorTab:
    def test_editor_tab_creation(self, qapp):
        tab = EditorTab()
        assert tab is not None
        assert tab.editor is not None
        assert tab.file_path is None

    def test_editor_tab_title_default(self, qapp):
        tab = EditorTab()
        assert tab.title == "未命名"

    def test_editor_tab_not_modified_initially(self, qapp):
        tab = EditorTab()
        assert tab.is_modified() is False

    def test_editor_tab_modified_after_insert(self, qapp):
        tab = EditorTab()
        tab.editor.textCursor().insertText("new content")
        assert tab.is_modified() is True

    def test_set_plain_text(self, qapp):
        tab = EditorTab()
        tab.set_plain_text("# Title")
        assert tab.editor.get_markdown() == "# Title"

    def test_file_path_title(self, qapp):
        tab = EditorTab()
        tab.file_path = "/path/to/document.md"
        assert tab.title == "document.md"


class TestTabManagerSignals:
    def test_editor_changed_signal_emitted(self, qapp):
        tm = TabManager()
        received = []
        tm.editor_changed.connect(lambda e: received.append(e))
        editor = tm.add_tab("Test")
        assert len(received) >= 1
        assert received[-1] is editor

    def test_has_unsaved_changes_false_initially(self, qapp):
        tm = TabManager()
        tm.add_tab("Test")
        assert tm.has_unsaved_changes() is False

    def test_has_unsaved_changes_true_after_edit(self, qapp):
        tm = TabManager()
        editor = tm.add_tab("Test")
        editor.textCursor().insertText("edited")
        assert tm.has_unsaved_changes() is True

    def test_has_unsaved_changes_false_after_modification_cleared(self, qapp):
        tm = TabManager()
        editor = tm.add_tab("Test")
        editor.setPlainText("edited")
        editor.document().setModified(False)
        assert tm.has_unsaved_changes() is False

    def test_set_tab_file_path_updates_tab(self, qapp):
        tm = TabManager()
        tm.add_tab("Test")
        tm.set_tab_file_path("/path/to/file.md")
        tab = tm.get_current_tab()
        assert tab.file_path == "/path/to/file.md"

    def test_update_tab_title(self, qapp):
        tm = TabManager()
        tm.add_tab("Original")
        tm.update_tab_title("Updated")
        tab = tm.get_current_tab()
        assert tab.title == "Updated"


class TestTabManagerEdgeCases:
    def test_apply_editor_settings_to_all_tabs(self, qapp):
        tm = TabManager()
        e1 = tm.add_tab("Tab 1")
        e2 = tm.add_tab("Tab 2")
        tm.apply_editor_settings({"font_size": 20})
        assert e1.font().pointSize() == 20
        assert e2.font().pointSize() == 20

    def test_apply_editor_settings_empty(self, qapp):
        tm = TabManager()
        e1 = tm.add_tab("Tab 1")
        tm.apply_editor_settings({})
        assert e1.font().pointSize() > 0

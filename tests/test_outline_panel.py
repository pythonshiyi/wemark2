from PySide6.QtCore import Qt

from ui.outline_panel import OutlinePanel


class TestOutlinePanel:
    def test_panel_creation(self, qapp):
        panel = OutlinePanel()
        assert panel is not None

    def test_update_outline_with_empty_markdown(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("")
        assert panel._tree.topLevelItemCount() == 0

    def test_update_outline_with_heading(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("# Heading 1")
        assert panel._tree.topLevelItemCount() == 1
        item = panel._tree.topLevelItem(0)
        assert item.text(0) == "Heading 1"

    def test_update_outline_multiple_headings(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("# H1\n## H2\n### H3")
        assert panel._tree.topLevelItemCount() == 1
        h1 = panel._tree.topLevelItem(0)
        assert h1.text(0) == "H1"
        assert h1.childCount() == 1
        h2 = h1.child(0)
        assert h2.text(0) == "H2"
        assert h2.childCount() == 1
        h3 = h2.child(0)
        assert h3.text(0) == "H3"

    def test_update_outline_stores_line_numbers(self, qapp):
        panel = OutlinePanel()
        text = "intro\n# H1\nbody\n## H2\nfooter"
        panel.update_outline(text)
        h1 = panel._tree.topLevelItem(0)
        assert h1.data(0, Qt.UserRole) == 2
        h2 = h1.child(0)
        assert h2.data(0, Qt.UserRole) == 4

    def test_heading_clicked_signal(self, qapp):
        panel = OutlinePanel()
        received = []
        panel.heading_clicked.connect(lambda ln: received.append(ln))
        panel.update_outline("# Title")
        item = panel._tree.topLevelItem(0)
        panel._on_item_clicked(item, 0)
        assert received == [1]

    def test_outline_ignores_non_heading_lines(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("paragraph\n- list\n> quote\n---")
        assert panel._tree.topLevelItemCount() == 0

    def test_outline_handles_headings_with_trailing_hashes(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("# Title #")
        assert panel._tree.topLevelItemCount() == 1
        assert panel._tree.topLevelItem(0).text(0) == "Title"

    def test_outline_hierarchy_nested_correctly(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("## H2\n# H1\n### H3")
        assert panel._tree.topLevelItemCount() == 2
        h2 = panel._tree.topLevelItem(0)
        assert h2.text(0) == "H2"
        h1 = panel._tree.topLevelItem(1)
        assert h1.text(0) == "H1"
        assert h1.childCount() == 1
        assert h1.child(0).text(0) == "H3"

    def test_headings_with_same_level(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("# H1a\n# H1b\n# H1c")
        assert panel._tree.topLevelItemCount() == 3

    def test_headings_with_leading_spaces(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("  # Indented Heading")
        assert panel._tree.topLevelItemCount() == 0


class TestOutlinePanelEdgeCases:
    def test_clear_and_reupdate(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("# First")
        panel.update_outline("# Second")
        assert panel._tree.topLevelItemCount() == 1
        assert panel._tree.topLevelItem(0).text(0) == "Second"

    def test_heading_with_no_trailing_text(self, qapp):
        panel = OutlinePanel()
        panel.update_outline("# ")
        assert panel._tree.topLevelItemCount() == 0

from ui.template_selector import TemplateSelector, TEMPLATE_LABELS, TEMPLATE_ORDER


class TestTemplateConstants:
    def test_template_labels_has_default(self):
        assert "default" in TEMPLATE_LABELS

    def test_template_labels_has_paper(self):
        assert "paper" in TEMPLATE_LABELS

    def test_template_order_matches_labels(self):
        for name in TEMPLATE_ORDER:
            assert name in TEMPLATE_LABELS

    def test_all_labels_have_display_names(self):
        for name, label in TEMPLATE_LABELS.items():
            assert isinstance(name, str)
            assert isinstance(label, str)
            assert len(label) > 0


class TestTemplateSelector:
    def test_template_selector_creation(self, qapp):
        sel = TemplateSelector()
        assert sel is not None
        assert sel.count() == len(TEMPLATE_ORDER)

    def test_default_template_is_first(self, qapp):
        sel = TemplateSelector()
        assert sel.current_template() == TEMPLATE_ORDER[0]

    def test_current_template_returns_current_selection(self, qapp):
        sel = TemplateSelector()
        sel.set_current_template("paper")
        assert sel.current_template() == "paper"

    def test_set_current_template_invalid(self, qapp):
        sel = TemplateSelector()
        current = sel.current_template()
        sel.set_current_template("nonexistent")
        assert sel.current_template() == current

    def test_template_changed_signal(self, qapp):
        sel = TemplateSelector()
        received = []
        sel.template_changed.connect(lambda t: received.append(t))
        sel.set_current_template("ocean")
        assert len(received) >= 1
        assert received[-1] == "ocean"

    def test_all_templates_accessible(self, qapp):
        sel = TemplateSelector()
        for name in TEMPLATE_ORDER:
            sel.set_current_template(name)
            assert sel.current_template() == name

    def test_refresh_keeps_selection(self, qapp):
        sel = TemplateSelector()
        sel.set_current_template("forest")
        sel.refresh()
        assert sel.current_template() == "forest"

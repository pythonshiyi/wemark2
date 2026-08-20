from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox,
    QPushButton, QFormLayout, QGroupBox, QCheckBox, QMessageBox,
    QPlainTextEdit, QSlider,
)
from PySide6.QtGui import QFont

from core.config import config_manager
from core.i18n import tr, set_language
from core.ai_client import ai_client


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("settings"))
        self.setMinimumSize(560, 520)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._create_ai_tab(), tr("settings_tab_ai"))
        tabs.addTab(self._create_editor_tab(), tr("settings_tab_editor"))
        tabs.addTab(self._create_image_host_tab(), tr("settings_tab_image_host"))
        tabs.addTab(self._create_typewriter_tab(), tr("settings_tab_typewriter"))
        tabs.addTab(self._create_template_tab(), tr("settings_tab_template"))
        tabs.addTab(self._create_general_tab(), tr("settings_tab_general"))

        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton(tr("settings_save"))
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton(tr("settings_cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._load()

    # ── AI 助手 ──

    def _create_ai_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        conn = QGroupBox(tr("settings_group_conn"))
        cl = QFormLayout(conn)
        self._ai_key = QLineEdit()
        self._ai_key.setEchoMode(QLineEdit.Password)
        self._ai_key.setPlaceholderText("sk-...")
        cl.addRow(tr("settings_ai_key"), self._ai_key)

        self._ai_url = QLineEdit()
        self._ai_url.setPlaceholderText("https://api.deepseek.com")
        cl.addRow(tr("settings_ai_url"), self._ai_url)

        self._ai_model = QComboBox()
        self._ai_model.setEditable(True)
        self._ai_model.addItem("deepseek-v4-flash", "deepseek-v4-flash")
        self._ai_model.addItem("deepseek-v4-pro", "deepseek-v4-pro")
        cl.addRow(tr("settings_ai_model"), self._ai_model)

        test_btn = QPushButton(tr("settings_test_conn"))
        test_btn.clicked.connect(self._test_connection)
        cl.addRow("", test_btn)
        layout.addRow(conn)

        params = QGroupBox(tr("settings_group_params"))
        pl = QFormLayout(params)
        self._ai_reasoning = QComboBox()
        self._ai_reasoning.addItem(tr("settings_reasoning_high"), "high")
        self._ai_reasoning.addItem(tr("settings_reasoning_max"), "max")
        pl.addRow(tr("settings_reasoning_label"), self._ai_reasoning)

        self._ai_thinking = QCheckBox(tr("settings_thinking"))
        pl.addRow("", self._ai_thinking)

        self._ai_thinking_hint = QLabel(tr("settings_thinking_hint"))
        self._ai_thinking_hint.setStyleSheet("color:#e67e22;font-size:10px;")
        self._ai_thinking_hint.setVisible(False)
        self._ai_thinking_hint.setWordWrap(True)
        pl.addRow("", self._ai_thinking_hint)
        self._ai_thinking.toggled.connect(self._on_thinking_toggled)

        self._ai_temp = QDoubleSpinBox()
        self._ai_temp.setRange(0.0, 2.0)
        self._ai_temp.setSingleStep(0.1)
        self._ai_temp.setValue(1.3)
        pl.addRow("Temperature:", self._ai_temp)

        self._ai_top_p = QDoubleSpinBox()
        self._ai_top_p.setRange(0.0, 1.0)
        self._ai_top_p.setSingleStep(0.05)
        self._ai_top_p.setValue(1.0)
        pl.addRow("Top P:", self._ai_top_p)

        self._ai_max_tokens = QSpinBox()
        self._ai_max_tokens.setRange(256, 384000)
        self._ai_max_tokens.setSingleStep(1024)
        self._ai_max_tokens.setValue(4096)
        self._ai_max_tokens.setToolTip(tr("settings_max_tokens_tip"))
        pl.addRow("Max Tokens:", self._ai_max_tokens)

        self._ai_max_turns = QSpinBox()
        self._ai_max_turns.setRange(2, 100)
        self._ai_max_turns.setValue(20)
        self._ai_max_turns.setToolTip(tr("settings_max_turns_tip"))
        pl.addRow(tr("settings_max_turns"), self._ai_max_turns)
        layout.addRow(params)

        price_group = QGroupBox(tr("settings_group_price"))
        price_ly = QVBoxLayout(price_group)
        price_label = QLabel(
            "📊 deepseek-v4-flash (Responses API 当前唯一支持)\n"
            "  输入: 1元/百万tokens | 输出: 2元\n"
            "📊 deepseek-v4-pro (Responses API 即将支持)\n"
            "  输入: 12元/百万tokens | 输出: 24元"
        )
        price_label.setStyleSheet("color:#888;font-size:11px;")
        price_ly.addWidget(price_label)
        layout.addRow(price_group)

        return w

    # ── 编辑器 ──

    def _create_editor_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        font_group = QGroupBox(tr("settings_group_font"))
        fl = QFormLayout(font_group)
        self._font_family = QComboBox()
        self._font_family.setEditable(True)
        for f in ["Consolas", "Microsoft YaHei", "Courier New", "Monaco", "Fira Code", "JetBrains Mono"]:
            self._font_family.addItem(f)
        fl.addRow(tr("settings_font_family"), self._font_family)

        self._font_size = QSpinBox()
        self._font_size.setRange(10, 36)
        self._font_size.setValue(16)
        fl.addRow(tr("settings_font_size"), self._font_size)

        self._line_spacing = QDoubleSpinBox()
        self._line_spacing.setRange(1.0, 3.0)
        self._line_spacing.setSingleStep(0.1)
        self._line_spacing.setValue(1.8)
        fl.addRow(tr("settings_line_spacing"), self._line_spacing)
        layout.addRow(font_group)

        behaviour = QGroupBox(tr("settings_group_behavior"))
        bl = QFormLayout(behaviour)
        self._tab_width = QSpinBox()
        self._tab_width.setRange(2, 8)
        self._tab_width.setValue(4)
        self._tab_width.setSuffix(tr("settings_tab_suffix"))
        bl.addRow(tr("settings_tab_width"), self._tab_width)

        self._word_wrap = QCheckBox(tr("settings_word_wrap"))
        self._word_wrap.setChecked(True)
        bl.addRow("", self._word_wrap)

        self._auto_pair = QCheckBox(tr("settings_auto_pair"))
        self._auto_pair.setChecked(True)
        bl.addRow("", self._auto_pair)

        self._snippet_expand = QCheckBox(tr("settings_snippet"))
        self._snippet_expand.setChecked(True)
        bl.addRow("", self._snippet_expand)

        self._show_line_nums = QCheckBox(tr("settings_show_line_nums"))
        self._show_line_nums.setChecked(True)
        bl.addRow("", self._show_line_nums)

        self._para_spacing = QComboBox()
        self._para_spacing.addItem(tr("settings_para_compact"), "compact")
        self._para_spacing.addItem(tr("settings_para_normal"), "normal")
        self._para_spacing.addItem(tr("settings_para_loose"), "loose")
        bl.addRow(tr("settings_para_spacing"), self._para_spacing)
        layout.addRow(behaviour)

        save_group = QGroupBox(tr("settings_group_autosave"))
        sl = QFormLayout(save_group)
        self._auto_save = QCheckBox(tr("settings_autosave"))
        sl.addRow("", self._auto_save)

        self._auto_save_interval = QSpinBox()
        self._auto_save_interval.setRange(10, 600)
        self._auto_save_interval.setValue(60)
        self._auto_save_interval.setSuffix(tr("settings_autosave_suffix"))
        self._auto_save_interval.setToolTip(tr("settings_autosave_tip"))
        sl.addRow(tr("settings_autosave_interval"), self._auto_save_interval)
        layout.addRow(save_group)

        return w

    # ── 图床 ──

    def _create_image_host_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        group = QGroupBox(tr("settings_group_image_host"))
        gl = QFormLayout(group)

        self._ih_uploader = QComboBox()
        self._ih_uploader.addItem(tr("settings_uploader_none"), "none")
        self._ih_uploader.addItem(tr("settings_uploader_catbox"), "catbox")
        self._ih_uploader.addItem(tr("settings_uploader_custom"), "custom")
        gl.addRow(tr("settings_image_uploader"), self._ih_uploader)

        self._ih_custom_url = QLineEdit()
        self._ih_custom_url.setPlaceholderText("https://your-host.com/upload")
        gl.addRow(tr("settings_custom_url"), self._ih_custom_url)

        self._ih_custom_field = QLineEdit("file")
        gl.addRow(tr("settings_custom_field"), self._ih_custom_field)

        self._ih_auto_insert = QCheckBox(tr("settings_auto_upload_insert"))
        gl.addRow("", self._ih_auto_insert)

        self._ih_auto_export = QCheckBox(tr("settings_auto_upload_export"))
        gl.addRow("", self._ih_auto_export)

        hint = QLabel(tr("settings_image_host_hint"))
        hint.setStyleSheet("color:#888;font-size:11px;")
        hint.setWordWrap(True)
        gl.addRow(hint)
        layout.addRow(group)

        self._ih_uploader.currentIndexChanged.connect(self._on_uploader_changed)
        return w

    def _on_uploader_changed(self, index: int):
        is_custom = self._ih_uploader.itemData(index) == "custom"
        self._ih_custom_url.setEnabled(is_custom)
        self._ih_custom_field.setEnabled(is_custom)

    # ── 打字机 ──

    def _create_typewriter_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self._focus_default = QCheckBox(tr("settings_focus_default"))
        layout.addRow("", self._focus_default)

        self._focus_opacity = QSpinBox()
        self._focus_opacity.setRange(30, 255)
        self._focus_opacity.setValue(160)
        self._focus_opacity.setToolTip(tr("settings_focus_opacity_tip"))
        layout.addRow(tr("settings_focus_opacity"), self._focus_opacity)

        self._scroll_default = QCheckBox(tr("settings_scroll_default"))
        layout.addRow("", self._scroll_default)

        self._scroll_pos = QSpinBox()
        self._scroll_pos.setRange(10, 90)
        self._scroll_pos.setValue(35)
        self._scroll_pos.setSuffix(" %")
        self._scroll_pos.setToolTip(tr("settings_scroll_pos_tip"))
        layout.addRow(tr("settings_scroll_pos"), self._scroll_pos)

        layout.addRow(QLabel(tr("settings_typewriter_desc")))

        return w

    # ── 排版 ──

    def _create_template_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        fl = QFormLayout()
        self._default_template = QComboBox()
        from ui.template_selector import TEMPLATE_ORDER, TEMPLATE_LABELS
        for name in TEMPLATE_ORDER:
            self._default_template.addItem(TEMPLATE_LABELS.get(name, name), name)
        fl.addRow(tr("settings_default_template"), self._default_template)
        layout.addLayout(fl)

        layout.addWidget(QLabel(tr("settings_custom_css")))
        self._custom_css = QPlainTextEdit()
        self._custom_css.setPlaceholderText(tr("settings_css_placeholder"))
        self._custom_css.setFont(QFont("Consolas", 11))
        self._custom_css.setMinimumHeight(160)
        self._custom_css.setStyleSheet(
            "QPlainTextEdit { border: 1px solid #ddd; border-radius: 4px; padding: 8px; "
            "background: #fafafa; }"
        )
        layout.addWidget(self._custom_css)

        return w

    # ── 常规 ──

    def _create_general_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self._language = QComboBox()
        self._language.addItem(tr("settings_zh"), "zh-CN")
        self._language.addItem("English", "en-US")
        layout.addRow(tr("settings_language"), self._language)

        self._theme = QComboBox()
        self._theme.addItem(tr("settings_light"), "light")
        self._theme.addItem(tr("settings_dark"), "dark")
        layout.addRow(tr("settings_theme"), self._theme)

        self._outline_default = QCheckBox(tr("settings_outline_default"))
        layout.addRow("", self._outline_default)

        return w

    # ── 逻辑 ──

    def _on_thinking_toggled(self, checked: bool):
        self._ai_thinking_hint.setVisible(checked)
        self._ai_temp.setEnabled(not checked)
        self._ai_top_p.setEnabled(not checked)

    def _load(self):
        c = config_manager
        self._ai_key.setText(c.get("ai.api_key", ""))
        self._ai_url.setText(c.get("ai.base_url", "https://api.deepseek.com"))

        model = c.get("ai.model", "deepseek-v4-flash")
        midx = self._ai_model.findData(model)
        if midx >= 0:
            self._ai_model.setCurrentIndex(midx)
        else:
            self._ai_model.setEditText(model)

        effort = c.get("ai.reasoning_effort", "high")
        eidx = self._ai_reasoning.findData(effort)
        if eidx >= 0:
            self._ai_reasoning.setCurrentIndex(eidx)

        self._ai_thinking.setChecked(c.get("ai.thinking_enabled", True))
        self._ai_temp.setValue(c.get("ai.temperature", 1.3))
        self._ai_top_p.setValue(c.get("ai.top_p", 1.0))
        self._ai_max_tokens.setValue(c.get("ai.max_tokens", 4096))
        self._ai_max_turns.setValue(c.get("ai.max_conversation_turns", 20))

        family = c.get("editor.font_family", "Consolas")
        idx = self._font_family.findText(family)
        if idx >= 0:
            self._font_family.setCurrentIndex(idx)
        else:
            self._font_family.setEditText(family)

        self._font_size.setValue(c.get("editor.font_size", 16))
        self._line_spacing.setValue(c.get("editor.line_spacing", 1.8))
        self._tab_width.setValue(c.get("editor.tab_width", 4))
        self._word_wrap.setChecked(c.get("editor.word_wrap", True))
        self._auto_pair.setChecked(c.get("editor.auto_pair", True))
        self._snippet_expand.setChecked(c.get("editor.snippet_expand", True))
        self._show_line_nums.setChecked(c.get("editor.show_line_numbers", True))

        spacing = c.get("editor.paragraph_spacing", "normal")
        sidx = self._para_spacing.findData(spacing)
        if sidx >= 0:
            self._para_spacing.setCurrentIndex(sidx)

        self._auto_save.setChecked(c.get("editor.auto_save", True))
        self._auto_save_interval.setValue(c.get("editor.auto_save_interval", 60))

        self._focus_default.setChecked(c.get("typewriter.focus_mode", False))
        self._focus_opacity.setValue(c.get("typewriter.focus_opacity", 160))
        self._scroll_default.setChecked(c.get("typewriter.typewriter_scroll", False))
        self._scroll_pos.setValue(int(c.get("typewriter.scroll_position", 0.35) * 100))

        default_tmpl = c.get("template.default", "default")
        tidx = self._default_template.findData(default_tmpl)
        if tidx >= 0:
            self._default_template.setCurrentIndex(tidx)
        self._custom_css.setPlainText(c.get("template.custom_css", ""))

        lang = c.get("language", "zh-CN")
        lidx = self._language.findData(lang)
        if lidx >= 0:
            self._language.setCurrentIndex(lidx)

        theme = c.get("theme", "light")
        tidx = self._theme.findData(theme)
        if tidx >= 0:
            self._theme.setCurrentIndex(tidx)

        self._outline_default.setChecked(c.get("outline_visible", False))

        uploader = c.get("image_host.uploader", "none")
        uidx = self._ih_uploader.findData(uploader)
        if uidx >= 0:
            self._ih_uploader.setCurrentIndex(uidx)
        self._ih_custom_url.setText(c.get("image_host.custom_url", ""))
        self._ih_custom_field.setText(c.get("image_host.custom_field", "file"))
        self._ih_auto_insert.setChecked(c.get("image_host.auto_upload_on_insert", False))
        self._ih_auto_export.setChecked(c.get("image_host.auto_upload_on_export", True))
        self._on_uploader_changed(self._ih_uploader.currentIndex())

    def _save(self):
        c = config_manager
        c.set("ai.api_key", self._ai_key.text())
        c.set("ai.base_url", self._ai_url.text())
        c.set("ai.model", self._ai_model.currentText())
        c.set("ai.reasoning_effort", self._ai_reasoning.currentData())
        c.set("ai.thinking_enabled", self._ai_thinking.isChecked())
        c.set("ai.temperature", self._ai_temp.value())
        c.set("ai.top_p", self._ai_top_p.value())
        c.set("ai.max_tokens", self._ai_max_tokens.value())
        c.set("ai.max_conversation_turns", self._ai_max_turns.value())

        c.set("editor.font_family", self._font_family.currentText())
        c.set("editor.font_size", self._font_size.value())
        c.set("editor.line_spacing", self._line_spacing.value())
        c.set("editor.tab_width", self._tab_width.value())
        c.set("editor.word_wrap", self._word_wrap.isChecked())
        c.set("editor.auto_pair", self._auto_pair.isChecked())
        c.set("editor.snippet_expand", self._snippet_expand.isChecked())
        c.set("editor.show_line_numbers", self._show_line_nums.isChecked())
        c.set("editor.paragraph_spacing", self._para_spacing.currentData())
        c.set("editor.auto_save", self._auto_save.isChecked())
        c.set("editor.auto_save_interval", self._auto_save_interval.value())

        c.set("typewriter.focus_mode", self._focus_default.isChecked())
        c.set("typewriter.focus_opacity", self._focus_opacity.value())
        c.set("typewriter.typewriter_scroll", self._scroll_default.isChecked())
        c.set("typewriter.scroll_position", self._scroll_pos.value() / 100.0)

        c.set("template.default", self._default_template.currentData())
        c.set("template.custom_css", self._custom_css.toPlainText())

        c.set("language", self._language.currentData())
        c.set("theme", self._theme.currentData())
        c.set("outline_visible", self._outline_default.isChecked())

        c.set("image_host.uploader", self._ih_uploader.currentData())
        c.set("image_host.custom_url", self._ih_custom_url.text())
        c.set("image_host.custom_field", self._ih_custom_field.text())
        c.set("image_host.auto_upload_on_insert", self._ih_auto_insert.isChecked())
        c.set("image_host.auto_upload_on_export", self._ih_auto_export.isChecked())
        set_language(self._language.currentData())

        ai_client.reload()
        self.accept()

    def _test_connection(self):
        api_key = self._ai_key.text()
        base_url = self._ai_url.text()
        if not api_key:
            QMessageBox.warning(self, tr("settings_test_conn"), tr("settings_fill_key"))
            return
        if not base_url:
            QMessageBox.warning(self, tr("settings_test_conn"), tr("settings_fill_url"))
            return

        from openai import OpenAI
        try:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)
            model = self._ai_model.currentText() or "deepseek-v4-flash"
            thinking = self._ai_thinking.isChecked()
            kwargs = dict(
                model=model,
                input=[{"role": "user", "content": "Hi"}],
                max_output_tokens=10,
            )
            kwargs["reasoning"] = {"effort": self._ai_reasoning.currentData() or "high" if thinking else "none"}
            client.responses.create(**kwargs)
            QMessageBox.information(self, tr("settings_test_conn"), tr("settings_test_ok"))
        except Exception as e:
            QMessageBox.warning(self, tr("settings_test_conn"), tr("settings_test_fail").format(error=str(e)))

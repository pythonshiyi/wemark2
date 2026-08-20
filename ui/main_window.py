import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar,
    QStatusBar, QPushButton, QLabel, QMenuBar, QMenu,
    QFileDialog, QMessageBox, QApplication, QProgressBar,
    QDockWidget, QDialog, QLineEdit,
)
from PySide6.QtGui import QAction, QKeySequence

from core.i18n import tr, set_language
from core.renderer import render_full_page
from core.clipboard import copy_rich_text
from core.config import config_manager
from core.logger import get_logger
from core.theme import DARK_STYLE, LIGHT_STYLE
from core.ai_client import ai_client

from ui.editor import Editor
from ui.preview import Preview, PreviewRenderWorker
from ui.upload_worker import ImageUploadWorker
from ui.tab_manager import TabManager
from ui.ai_panel import AIPanel
from ui.outline_panel import OutlinePanel
from ui.template_selector import TemplateSelector
from ui.settings_dialog import SettingsDialog
from ui.export_dialog import ExportDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = get_logger("main_window")
        self._base_title = tr("app_title")

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(200)
        self._preview_timer.timeout.connect(self._render_preview)
        self._preview_worker = None
        self._preview_pending = False
        self._preview_gen = 0
        self._upload_workers = []

        self._init_ui()
        self._init_menu()
        self._init_bindings()
        self._restore_geometry()
        self._apply_theme()

        interval = config_manager.get("editor.auto_save_interval", 60) * 1000
        self._auto_save_timer.start(interval)

        template = config_manager.get("template.last_used", "default")
        self._template_selector.set_current_template(template)

        self._apply_editor_state()
        self._sync_menu_toggles()
        self.setWindowTitle(self._base_title)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        tbw = QWidget()
        tbly = QHBoxLayout(tbw)
        tbly.setContentsMargins(12, 6, 12, 6)
        tbly.setSpacing(10)

        self._template_label = QLabel(tr("template_label"), styleSheet="color:#777;font-size:13px;")
        tbly.addWidget(self._template_label)
        self._template_selector = TemplateSelector()
        tbly.addWidget(self._template_selector)
        tbly.addStretch()

        # Markdown 格式工具栏
        md_actions = [
            ("B", tr("toolbar_bold"), lambda: self._editor_act("apply_bold"), "font-weight:bold;"),
            ("I", tr("toolbar_italic"), lambda: self._editor_act("apply_italic"), "font-style:italic;"),
            ("S", tr("toolbar_strikethrough"), lambda: self._editor_act("apply_strikethrough"), "text-decoration:line-through;"),
            ("`", tr("toolbar_code"), lambda: self._editor_act("apply_code"), "font-family:Consolas;"),
            ("H1", tr("toolbar_heading1"), lambda: self._editor_act("apply_heading", 1), ""),
            ("H2", tr("toolbar_heading2"), lambda: self._editor_act("apply_heading", 2), ""),
            ("H3", tr("toolbar_heading3"), lambda: self._editor_act("apply_heading", 3), ""),
            ("「」", tr("toolbar_quote"), lambda: self._editor_act("apply_quote"), ""),
            ("•", tr("toolbar_ulist"), lambda: self._editor_act("apply_list", False), ""),
            ("1.", tr("toolbar_olist"), lambda: self._editor_act("apply_list", True), ""),
            ("🔗", tr("toolbar_link"), lambda: self._editor_act("apply_link"), ""),
            ("◇", tr("toolbar_code_block"), lambda: self._editor_act("apply_code_block"), ""),
            ("🖼", tr("toolbar_image"), lambda: self._editor_act("apply_image"), "font-size:14px;"),
            ("⊞", tr("toolbar_table"), lambda: self._editor_act("apply_table"), ""),
            ("—", tr("toolbar_hr"), lambda: self._editor_act("apply_hr"), ""),
            ("≡", tr("toolbar_format"), lambda: self._editor_act("format_markdown"), "font-weight:bold;"),
        ]
        md_style = (
            "QPushButton{background:transparent;color:#666;border:1px solid #ddd;"
            "border-radius:3px;padding:3px 8px;font-size:12px;min-width:24px;}"
            "QPushButton:hover{background:#e8e8e8;border-color:#bbb;color:#333;}"
        )
        for label, tip, slot, extra in md_actions:
            btn = QPushButton(label)
            btn.setToolTip(tip)
            btn.setStyleSheet(md_style + extra)
            btn.clicked.connect(slot)
            tbly.addWidget(btn)

        sep = QLabel("│", styleSheet="color:#ddd;padding:0 2px;")
        tbly.addWidget(sep)

        ai_actions = [
            ("✍", tr("toolbar_ai_continue"), "continue_writing"),
            ("✨", tr("toolbar_ai_polish"), "polish"),
            ("🌐", tr("toolbar_ai_translate"), "translate"),
            ("📋", tr("toolbar_ai_summarize"), "summarize"),
        ]
        ai_style = (
            "QPushButton{background:#f0e6ff;color:#7c3aed;border:1px solid #d4bfff;"
            "border-radius:3px;padding:3px 8px;font-size:12px;min-width:24px;}"
            "QPushButton:hover{background:#e0ccff;border-color:#b088e0;color:#5b21b6;}"
        )
        for label, tip, action in ai_actions:
            btn = QPushButton(label)
            btn.setToolTip(tip)
            btn.setStyleSheet(ai_style)
            btn.clicked.connect(lambda checked=False, a=action: self._trigger_ai_action(a))
            tbly.addWidget(btn)

        tbly.addStretch()

        btn_base = (
            "QPushButton{font-weight:bold;padding:6px 14px;border-radius:4px;"
            "font-size:12px;}"
        )
        self._copy_wx_btn = QPushButton(f"📋 {tr('btn_copy_wechat')}")
        self._copy_wx_btn.setStyleSheet(
            btn_base
            + "QPushButton{background-color:#07C160;color:#fff;border:none;}"
            "QPushButton:hover{background-color:#06AD56;}")
        self._copy_wx_btn.setToolTip(tr("tip_copy_wechat"))
        tbly.addWidget(self._copy_wx_btn)

        self._copy_img_btn = QPushButton(f"🖼 {tr('btn_copy_image')}")
        self._copy_img_btn.setStyleSheet(
            btn_base
            + "QPushButton{background-color:#e8f5e9;color:#2e7d32;"
            "border:1px solid #a5d6a7;}"
            "QPushButton:hover{background-color:#c8e6c9;}")
        self._copy_img_btn.setToolTip(tr("tip_copy_image"))
        tbly.addWidget(self._copy_img_btn)

        self._export_btn = QPushButton(f"📦 {tr('btn_export')}")
        self._export_btn.setStyleSheet(
            btn_base
            + "QPushButton{background-color:#f0f0f0;color:#555;"
            "border:1px solid #ddd;}"
            "QPushButton:hover{background-color:#e0e0e0;color:#333;}")
        self._export_btn.setToolTip(tr("tip_export"))
        tbly.addWidget(self._export_btn)
        toolbar.addWidget(tbw)

        from PySide6.QtGui import QShortcut, QKeySequence

        QShortcut(QKeySequence("Ctrl+Shift+E"), self, self._show_export)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self._copy_to_wechat)
        QShortcut(QKeySequence("Ctrl+Shift+I"), self, self._copy_preview_image)
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+G"), self, self._go_to_line)
        QShortcut(QKeySequence("F3"), self, self._find_next)
        QShortcut(QKeySequence("Shift+F3"), self, self._find_previous)

        self._tab_manager = TabManager()
        self._tab_manager.add_tab(tr("untitled"))

        self._preview = Preview()
        self._preview.scroll_percent_changed.connect(self._on_preview_scroll)
        self._preview_dock = QDockWidget(tr("preview_tab"), self)
        self._preview_dock.setObjectName("preview_dock")
        self._preview_dock.setWidget(self._preview)
        self._preview_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self._preview_dock)

        self._ai_panel = AIPanel()
        self._ai_panel.set_context_getter(self._get_ai_context)
        self._ai_panel.insert_requested.connect(self._ai_insert)
        self._ai_panel.new_tab_requested.connect(self._ai_open_tab)
        self._ai_dock = QDockWidget(tr("ai_tab"), self)
        self._ai_dock.setObjectName("ai_dock")
        self._ai_dock.setWidget(self._ai_panel)
        self._ai_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._ai_dock)

        self._outline = OutlinePanel()
        self._outline.heading_clicked.connect(self._goto_line)
        self._outline_dock = QDockWidget(tr("outline_title"), self)
        self._outline_dock.setObjectName("outline_dock")
        self._outline_dock.setWidget(self._outline)
        self._outline_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._outline_dock)
        if not config_manager.get("outline_visible", False):
            self._outline_dock.hide()

        main_layout.addWidget(self._tab_manager)

        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(
            "QStatusBar{background:#f8f9fa;border-top:1px solid #e0e0e0;}"
            "QStatusBar::item{border:none;}"
        )
        self.setStatusBar(self._status_bar)

        self._word_label = QLabel("")
        self._word_label.setStyleSheet("color:#888;font-size:11px;padding:0 8px;")
        self._status_bar.addPermanentWidget(self._word_label)

        self._cursor_label = QLabel("", styleSheet="color:#aaa;font-size:11px;padding:0 8px;")
        self._status_bar.addPermanentWidget(self._cursor_label)

        self._focus_label = QLabel("",
            styleSheet="color:#9c27b0;font-size:10px;font-weight:bold;padding:2px 8px;"
                       "background:#f3e8ff;border-radius:3px;margin:2px 2px;")
        self._focus_label.setVisible(False)
        self._status_bar.addPermanentWidget(self._focus_label)

        self._typewriter_label = QLabel("",
            styleSheet="color:#e67e22;font-size:10px;font-weight:bold;padding:2px 8px;"
                       "background:#fef3e7;border-radius:3px;margin:2px 2px;")
        self._typewriter_label.setVisible(False)
        self._status_bar.addPermanentWidget(self._typewriter_label)

        self._auto_save_label = QLabel("",
            styleSheet="color:#4caf50;font-size:10px;padding:0 8px;")
        self._status_bar.addPermanentWidget(self._auto_save_label)

        self._progress_bar = QProgressBar(visible=False, fixedWidth=150,
            styleSheet="QProgressBar{border:1px solid #e0e0e0;border-radius:3px;"
                       "text-align:center;font-size:10px;height:14px;}"
                       "QProgressBar::chunk{background:#1a73e8;border-radius:2px;}")
        self._progress_bar.setRange(0, 0)
        self._status_bar.addPermanentWidget(self._progress_bar)

    def _init_menu(self):
        mb = self.menuBar()

        # ── 文件 ──
        file_menu = mb.addMenu(tr("file_menu"))
        for name, shortcut, slot in [
            ("new_file", "Ctrl+N", self._new_file),
            ("open_file", "Ctrl+O", self._open_file),
            ("save_file", "Ctrl+S", self._save),
            ("save_as", "Ctrl+Shift+S", self._save_as),
        ]:
            a = QAction(tr(name), self, shortcut=shortcut, triggered=slot)
            file_menu.addAction(a)
        file_menu.addSeparator()
        file_menu.addAction(QAction(tr("exit_app"), self, shortcut="Ctrl+Q", triggered=self.close))
        self._recent_menu = file_menu.addMenu(tr("recent_files"))
        self._update_recent_menu()

        # ── 编辑 ──
        edit_menu = mb.addMenu(tr("edit_menu"))
        for name, shortcut, slot in [
            ("undo", "Ctrl+Z", lambda: self._editor.undo() if self._editor else None),
            ("redo", "Ctrl+Shift+Z", lambda: self._editor.redo() if self._editor else None),
        ]:
            edit_menu.addAction(QAction(tr(name), self, shortcut=shortcut, triggered=slot))
        edit_menu.addSeparator()
        for name, shortcut, slot in [
            ("cut", "Ctrl+X", lambda: self._editor.cut() if self._editor else None),
            ("copy", "Ctrl+C", lambda: self._editor.copy() if self._editor else None),
            ("paste", "Ctrl+V", lambda: self._editor.paste() if self._editor else None),
            ("select_all", "Ctrl+A", lambda: self._editor.selectAll() if self._editor else None),
        ]:
            edit_menu.addAction(QAction(tr(name), self, shortcut=shortcut, triggered=slot))
        edit_menu.addSeparator()
        edit_menu.addAction(QAction(tr("find_replace"), self, shortcut="Ctrl+F", triggered=self._show_find))

        # ── 格式 ──
        fmt_menu = mb.addMenu(tr("menu_format"))
        fmt_actions = [
            (f"{tr('menu_bold')}\tCtrl+B", lambda: self._editor_act("apply_bold")),
            (f"{tr('menu_italic')}\tCtrl+I", lambda: self._editor_act("apply_italic")),
            (f"{tr('menu_strikethrough')}\tCtrl+Shift+S", lambda: self._editor_act("apply_strikethrough")),
            (f"{tr('menu_inline_code')}\tCtrl+Shift+C", lambda: self._editor_act("apply_code")),
        ]
        for label, slot in fmt_actions:
            fmt_menu.addAction(label, slot)
        fmt_menu.addSeparator()
        for label, slot in [
            (tr("menu_heading1"), lambda: self._editor_act("apply_heading", 1)),
            (tr("menu_heading2"), lambda: self._editor_act("apply_heading", 2)),
            (tr("menu_heading3"), lambda: self._editor_act("apply_heading", 3)),
            (tr("menu_quote"), lambda: self._editor_act("apply_quote")),
            (tr("menu_ulist"), lambda: self._editor_act("apply_list")),
            (tr("menu_olist"), lambda: self._editor_act("apply_list", True)),
            (tr("menu_code_block"), lambda: self._editor_act("apply_code_block")),
            (tr("menu_table"), lambda: self._editor_act("apply_table")),
            (tr("menu_hr"), lambda: self._editor_act("apply_hr")),
            (tr("menu_link"), lambda: self._editor_act("apply_link")),
            (tr("menu_image"), lambda: self._editor_act("apply_image")),
        ]:
            fmt_menu.addAction(label, slot)
        fmt_menu.addSeparator()
        fmt_menu.addAction(tr("menu_format_doc"), lambda: self._editor_act("format_markdown"))

        # ── AI (新增) ──
        ai_menu = mb.addMenu(tr("menu_ai"))
        for label, action in [
            (f"✍ {tr('menu_ai_continue')}\tCtrl+Shift+W", "continue_writing"),
            (f"✨ {tr('menu_ai_polish')}\tCtrl+Shift+P", "polish"),
            (f"🌐 {tr('menu_ai_translate')}\tCtrl+Shift+T", "translate"),
            (f"📋 {tr('menu_ai_summarize')}\tCtrl+Shift+M", "summarize"),
        ]:
            a = QAction(label, self, triggered=lambda a=action: self._trigger_ai_action(a))
            ai_menu.addAction(a)
        ai_menu.addSeparator()
        a = QAction(tr("menu_ai_chat"), self, shortcut="Ctrl+Shift+A")
        a.triggered.connect(lambda: self._ai_dock.setVisible(not self._ai_dock.isVisible()))
        ai_menu.addAction(a)

        # ── 视图 ──
        view_menu = mb.addMenu(tr("view_menu"))

        def _add_action(menu, label, shortcut, slot):
            a = QAction(label, self, shortcut=shortcut)
            a.triggered.connect(slot)
            menu.addAction(a)

        _add_action(view_menu, tr("menu_preview"), "Ctrl+P",
                    lambda: self._preview_dock.setVisible(not self._preview_dock.isVisible()))
        _add_action(view_menu, tr("menu_outline"), "Ctrl+Shift+O", self._toggle_outline)
        view_menu.addSeparator()

        _add_action(view_menu, tr("menu_focus_mode"), "Ctrl+J",
                    lambda: self._editor_act("_toggle_focus_mode") if self._editor else None)
        _add_action(view_menu, tr("menu_typewriter"), "Ctrl+L",
                    lambda: self._editor_act("_toggle_typewriter_scroll") if self._editor else None)
        view_menu.addSeparator()

        self._menu_show_line_nums = QAction(tr("menu_show_line_numbers"), self, checkable=True,
                                            triggered=lambda: self._toggle_line_numbers())
        view_menu.addAction(self._menu_show_line_nums)
        self._menu_auto_pair = QAction(tr("menu_auto_pair"), self, checkable=True,
                                       triggered=lambda: self._toggle_auto_pair())
        view_menu.addAction(self._menu_auto_pair)
        self._menu_snippet = QAction(tr("menu_snippet"), self, checkable=True,
                                     triggered=lambda: self._toggle_snippet())
        view_menu.addAction(self._menu_snippet)
        view_menu.addSeparator()

        for name, shortcut, slot in [
            (tr("menu_zoom_in"), "Ctrl+=", self._zoom_in),
            (tr("menu_zoom_out"), "Ctrl+-", self._zoom_out),
            (tr("menu_zoom_reset"), "Ctrl+0", self._zoom_reset),
        ]:
            a = QAction(name, self, shortcut=shortcut)
            a.triggered.connect(slot)
            view_menu.addAction(a)
        view_menu.addSeparator()

        a = QAction(tr("menu_swap_layout"), self, shortcut="Ctrl+Shift+L")
        a.triggered.connect(self._swap_layout)
        view_menu.addAction(a)
        a = QAction(tr("menu_reset_layout"), self)
        a.triggered.connect(self._reset_layout)
        view_menu.addAction(a)
        view_menu.addSeparator()

        zen = QAction(tr("menu_fullscreen"), self, shortcut="F11", checkable=True)
        zen.triggered.connect(lambda: self.showFullScreen() if not self.isFullScreen() else self.showNormal())
        view_menu.addAction(zen)
        a = QAction(tr("toggle_dark_mode"), self, shortcut="F10")
        a.triggered.connect(self._toggle_theme)
        view_menu.addAction(a)

        # ── 设置 ──
        settings_menu = mb.addMenu(tr("settings_menu"))
        settings_menu.addAction(QAction(tr("settings"), self, shortcut="Ctrl,", triggered=self._show_settings))

        # ── 帮助 ──
        help_menu = mb.addMenu(tr("help_menu"))
        help_menu.addAction(QAction(tr("about"), self, triggered=self._show_about))

    def _init_bindings(self):
        self._tab_manager.editor_changed.connect(self._on_editor_changed)
        self._tab_manager.file_changed.connect(self._on_file_changed)
        self._template_selector.template_changed.connect(self._on_template_changed)
        self._copy_wx_btn.clicked.connect(self._copy_to_wechat)
        self._copy_img_btn.clicked.connect(self._copy_preview_image)
        self._export_btn.clicked.connect(self._show_export)

        editor = self._editor
        if editor:
            self._connect_editor(editor)

    def _on_editor_changed(self, editor: Editor):
        self._connect_editor(editor)
        if editor:
            self._apply_editor_settings(editor)
            self._apply_editor_state()
            self._update_counts()
            self._preview_timer.start()

    def _on_file_changed(self, path: str):
        self.setWindowTitle(f"{os.path.basename(path)} — {self._base_title}")

    def _connect_editor(self, editor: Editor):
        if not editor:
            return
        try:
            if hasattr(self, '_current_editor') and self._current_editor:
                try:
                    self._current_editor.textChanged.disconnect(self._update_counts)
                    self._current_editor.cursor_line_changed.disconnect(self._update_cursor_pos)
                except (TypeError, RuntimeError):
                    pass
            self._current_editor = editor
            editor.set_on_change_callback(self._on_content_changed)
            editor.textChanged.connect(self._update_counts)
            editor.cursor_line_changed.connect(self._update_cursor_pos)
            editor.mode_changed.connect(lambda: self._update_mode_indicators(editor))
            editor.ai_action_requested.connect(self._on_ai_action)
            self._update_mode_indicators(editor)
        except Exception:
            pass

    def _toggle_line_numbers(self):
        checked = self._menu_show_line_nums.isChecked()
        config_manager.set("editor.show_line_numbers", checked)
        if self._editor:
            self._editor._update_line_number_area()
            self._editor.viewport().update()

    def _toggle_auto_pair(self):
        checked = self._menu_auto_pair.isChecked()
        config_manager.set("editor.auto_pair", checked)

    def _toggle_snippet(self):
        checked = self._menu_snippet.isChecked()
        config_manager.set("editor.snippet_expand", checked)

    def _apply_editor_state(self):
        editor = self._editor
        if not editor:
            return
        editor._update_line_number_area()
        focus = config_manager.get("typewriter.focus_mode", False)
        if focus:
            editor._focus_mode = True
            editor.viewport().update()
        tscroll = config_manager.get("typewriter.typewriter_scroll", False)
        if tscroll:
            editor._typewriter_scroll = True
        self._update_mode_indicators(editor)

    def _sync_menu_toggles(self):
        self._menu_show_line_nums.setChecked(config_manager.get("editor.show_line_numbers", True))
        self._menu_auto_pair.setChecked(config_manager.get("editor.auto_pair", True))
        self._menu_snippet.setChecked(config_manager.get("editor.snippet_expand", True))

    def _update_mode_indicators(self, editor: Editor = None):
        e = editor or self._editor
        if not e:
            self._focus_label.setVisible(False)
            self._typewriter_label.setVisible(False)
            return
        self._focus_label.setText(tr("status_focus_mode") if getattr(e, '_focus_mode', False) else "")
        self._focus_label.setVisible(getattr(e, '_focus_mode', False))
        self._typewriter_label.setText(tr("status_typewriter") if getattr(e, '_typewriter_scroll', False) else "")
        self._typewriter_label.setVisible(getattr(e, '_typewriter_scroll', False))

    def _on_content_changed(self):
        self._preview_timer.start()
        self._update_counts()
        self._tab_manager._update_tab_display(self._tab_manager.current_index())
        # 更新大纲
        editor = self._editor
        if editor:
            self._outline.update_outline(editor.get_markdown())
        # 预览滚动同步（编辑器→预览）
        if editor:
            sb = editor.verticalScrollBar()
            self._preview.set_scroll_percent(
                sb.value() / max(1, sb.maximum())
            )

    def _on_preview_scroll(self, pct: float):
        """预览滚动同步回编辑器。"""
        editor = self._editor
        if editor:
            editor.scroll_to_percent(pct)

    def _on_template_changed(self, name: str):
        config_manager.set("template.last_used", name)
        self._preview_timer.start()

    def _render_preview(self):
        editor = self._editor
        if not editor or not self._preview_dock.isVisible():
            return
        if self._preview_worker and self._preview_worker.isRunning():
            self._preview_pending = True
            return
        self._preview_pending = False
        self._preview_gen += 1
        worker = PreviewRenderWorker(
            editor.get_markdown(),
            self._template_selector.current_template(),
            self._preview_gen,
        )
        worker.rendered.connect(self._on_preview_rendered)
        self._preview_worker = worker
        worker.start()

    def _on_preview_rendered(self, gen: int, html: str):
        if gen != self._preview_gen:
            return
        self._preview.display_html(html)
        if self._preview_pending:
            self._preview_timer.start()

    def _update_counts(self):
        editor = self._editor
        if not editor:
            self._word_label.setText("")
            return
        text = editor.get_markdown()

        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_words = len([w for w in text.split() if w.isascii() and w.isalpha()])
        total_chars = len(text.replace("\n", "").replace(" ", ""))
        paragraphs = max(1, len([p for p in text.split("\n") if p.strip()]))
        lines = text.count("\n") + 1

        read_time = max(1, round(total_chars / 300)) if total_chars > 0 else 1
        label_text = tr("status_word_count",
               chinese=chinese_chars, english=english_words,
               para=paragraphs, lines=lines,
               read_time=read_time)
        if total_chars >= 15000:
            label_text += tr("status_word_count_warn")
        color = "#888"
        if total_chars >= 19000:
            color = "#e53935"
        elif total_chars >= 15000:
            color = "#e67e22"
        self._word_label.setStyleSheet(f"color:{color};font-size:11px;padding:0 8px;")
        self._word_label.setText(label_text)

    def _update_cursor_pos(self, line: int, total: int):
        self._cursor_label.setText(tr("status_cursor_pos", line=line, total=total))

    def _get_ai_context(self) -> str:
        editor = self._editor
        if not editor:
            return ""
        cursor = editor.textCursor()
        return cursor.selectedText().replace("\u2029", "\n") if cursor.hasSelection() else ""

    def _trigger_ai_action(self, action: str):
        editor = self._editor
        if not editor:
            return
        cursor = editor.textCursor()
        selection = cursor.selectedText().replace("\u2029", "\n") if cursor.hasSelection() else ""
        self._on_ai_action(action, selection)

    def _on_ai_action(self, action: str, selection: str):
        editor = self._editor
        if not editor:
            return
        context = selection or editor.get_markdown()
        if not context.strip():
            self._status_bar.showMessage(tr("status_no_content"), 2000)
            return
        if not ai_client.available:
            QMessageBox.warning(self, tr("ai_not_configured_title"), tr("ai_not_configured_msg"))
            return
        if not self._ai_dock.isVisible():
            self._ai_dock.show()
        self._ai_panel._ensure_visible()
        self._ai_panel.execute_action(action, context, editor.get_markdown())
        _ai_tr_keys = {
            "continue_writing": "menu_ai_continue",
            "polish": "menu_ai_polish",
            "translate": "menu_ai_translate",
            "summarize": "menu_ai_summarize",
        }
        label = tr(_ai_tr_keys.get(action, action))
        self._status_bar.showMessage(tr("status_ai_processing", action=label), 5000)

    def _ai_insert(self, text: str):
        editor = self._editor
        if editor:
            cursor = editor.textCursor()
            cursor.insertText(text)
            editor.setTextCursor(cursor)
            editor.setFocus()

    def _ai_open_tab(self, text: str):
        self._tab_manager.add_tab(text.split("\n")[0][:30], text)

    def _apply_editor_settings(self, editor: Editor):
        editor.update_settings(config_manager.get("editor") or {})

    def _new_file(self):
        self._tab_manager.add_tab(tr("untitled"))

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("open_file_title"), "", "Markdown (*.md *.markdown);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, tr("error_title"), tr("error_open_file", error=str(e)))
            return

        editor = self._editor
        tab = self._tab_manager.get_current_tab()
        if editor and tab and not editor.get_markdown() and not tab.file_path:
            editor.setPlainText(content)
            self._tab_manager.set_tab_file_path(path)
        else:
            self._tab_manager.add_tab(os.path.basename(path), content)
            self._tab_manager.set_tab_file_path(path)
        self._add_recent_file(path)

    def _save(self):
        tab = self._tab_manager.get_current_tab()
        if not tab:
            return
        if tab.file_path:
            self._save_to_path(tab.file_path)
        else:
            self._save_as()

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("save_file_title"), "", "Markdown (*.md);;All Files (*)")
        if path:
            self._save_to_path(path)
            self._tab_manager.set_tab_file_path(path)

    def _save_to_path(self, path: str):
        editor = self._editor
        if editor:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(editor.get_markdown())
                editor.document().setModified(False)
                self._tab_manager._update_tab_display(self._tab_manager.current_index())
                self._show_autosave_indicator(tr("status_saved"))
                self._add_recent_file(path)
            except Exception as e:
                QMessageBox.warning(self, tr("error_title"), tr("error_save_file", error=str(e)))

    def _auto_save(self):
        if not config_manager.get("editor.auto_save", True):
            return
        editor = self._editor
        tab = self._tab_manager.get_current_tab()
        if editor and tab and tab.file_path and editor.document().isModified():
            try:
                with open(tab.file_path, "w", encoding="utf-8") as f:
                    f.write(editor.get_markdown())
                editor.document().setModified(False)
                self._tab_manager._update_tab_display(self._tab_manager.current_index())
                self._show_autosave_indicator(tr("status_autosaved"))
            except Exception as e:
                self.logger.error(f"Auto-save failed for {tab.file_path}: {e}")
                self._status_bar.showMessage(
                    f"{tr('error_title')}: {tr('status_autosave_failed')}",
                    5000,
                )

    def _show_autosave_indicator(self, msg: str):
        self._auto_save_label.setText(msg)
        QTimer.singleShot(3000, self._clear_autosave)

    def show_progress(self, visible: bool = True):
        self._progress_bar.setVisible(visible)

    def set_progress_text(self, text: str):
        self._progress_bar.setFormat(text if text else "")

    def _clear_autosave(self):
        if self._auto_save_label:
            self._auto_save_label.setText("")

    def _editor_act(self, method_name: str, *args):
        """调用当前编辑器的格式化方法。"""
        editor = self._editor
        if editor:
            method = getattr(editor, method_name, None)
            if method:
                method(*args)
                editor.setFocus()

    @property
    def _editor(self) -> Editor:
        return self._tab_manager.get_current_editor()

    def _goto_line(self, line: int):
        editor = self._editor
        if editor:
            editor.scroll_to_line(line)
            editor.setFocus()

    def _show_find(self):
        editor = self._editor
        if not editor:
            return
        if hasattr(self, '_find_dialog') and self._find_dialog and self._find_dialog.isVisible():
            self._find_dialog.raise_()
            self._find_dialog.activateWindow()
            return

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QCheckBox

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("find_title"))
        dialog.setMinimumWidth(420)
        dialog.setAttribute(Qt.WA_DeleteOnClose, False)
        layout = QVBoxLayout(dialog)

        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText(tr("find_placeholder"))
        layout.addWidget(self._find_input)

        opt_row = QHBoxLayout()
        self._find_case = QCheckBox(tr("find_case_sensitive"))
        self._find_whole = QCheckBox(tr("find_whole_word"))
        self._find_regex = QCheckBox(tr("find_regex"))
        opt_row.addWidget(self._find_case)
        opt_row.addWidget(self._find_whole)
        opt_row.addWidget(self._find_regex)
        layout.addLayout(opt_row)

        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText(tr("replace_placeholder"))
        layout.addWidget(self._replace_input)

        btn_layout = QHBoxLayout()
        find_btn = QPushButton(tr("find_next"))
        find_btn.clicked.connect(lambda: self._do_find())
        btn_layout.addWidget(find_btn)
        replace_btn = QPushButton(tr("find_replace"))
        replace_btn.clicked.connect(lambda: self._do_replace())
        btn_layout.addWidget(replace_btn)
        replace_all_btn = QPushButton(tr("find_replace_all"))
        replace_all_btn.clicked.connect(lambda: self._do_replace_all())
        btn_layout.addWidget(replace_all_btn)
        layout.addLayout(btn_layout)

        self._find_dialog = dialog
        self._find_input.setFocus()
        dialog.show()

    def _do_find(self):
        editor = self._editor
        if not editor or not self._find_input.text():
            return
        case = self._find_case.isChecked()
        whole = self._find_whole.isChecked()
        regex = self._find_regex.isChecked()
        editor.find_text_ext(self._find_input.text(), case_sensitive=case, whole_word=whole, regex=regex)

    def _do_replace(self):
        editor = self._editor
        if not editor or not self._find_input.text():
            return
        case = self._find_case.isChecked()
        whole = self._find_whole.isChecked()
        regex = self._find_regex.isChecked()
        editor.find_replace_one(self._find_input.text(), self._replace_input.text(), case_sensitive=case, whole_word=whole, regex=regex)

    def _do_replace_all(self):
        editor = self._editor
        if not editor or not self._find_input.text():
            return
        case = self._find_case.isChecked()
        whole = self._find_whole.isChecked()
        regex = self._find_regex.isChecked()
        count = editor.find_replace_all(self._find_input.text(), self._replace_input.text(), case_sensitive=case, whole_word=whole, regex=regex)
        msg = tr("status_replaced").format(count=count) if count > 0 else ""
        if msg:
            self._status_bar.showMessage(msg, 3000)

    def _copy_to_wechat(self):
        editor = self._editor
        if not editor:
            return
        md = editor.get_markdown()
        tmpl = self._template_selector.current_template()
        html = render_full_page(md, tmpl)
        tab = self._tab_manager.get_current_tab()
        base = os.path.dirname(tab.file_path) if tab and tab.file_path else None

        from core import image_hosting
        if image_hosting.is_enabled() and config_manager.get("image_host.auto_upload_on_export", True):
            self._upload_and_copy_wechat(html, base)
            return

        copy_rich_text(html, base)
        self._status_bar.showMessage(tr("status_copied_wechat"), 3000)

    def _upload_and_copy_wechat(self, html: str, base: str):
        self._status_bar.showMessage(tr("status_image_uploading"), 5000)
        self.show_progress(True)
        self.set_progress_text(tr("status_image_uploading"))
        worker = ImageUploadWorker(html, base)
        worker.done.connect(lambda new_html, count: self._on_upload_done(new_html, count))
        worker.error.connect(lambda err: self._on_upload_error(err))
        self._upload_workers.append(worker)
        worker.start()

    def _on_upload_done(self, html: str, count: int):
        self.show_progress(False)
        self._upload_workers.clear()
        copy_rich_text(html, None)
        if count > 0:
            self._status_bar.showMessage(tr("status_images_uploaded", count=count), 5000)
        else:
            self._status_bar.showMessage(tr("status_copied_wechat"), 3000)

    def _on_upload_error(self, err: str):
        self.show_progress(False)
        self._upload_workers.clear()
        self._status_bar.showMessage(tr("image_host_upload_failed", error=err), 5000)

    def _copy_preview_image(self):
        """复制预览内容为高清长图（QTextDocument 原生渲染）。"""
        editor = self._editor
        if not editor:
            return
        md = editor.get_markdown()
        if not md.strip():
            self._status_bar.showMessage(tr("status_no_content_copy"), 2000)
            return
        self._preview.capture_to_clipboard(md)
        self._status_bar.showMessage(tr("status_copied_image"), 3000)

    def _show_export(self):
        editor = self._editor
        if not editor:
            return
        md = editor.get_markdown()
        tmpl = self._template_selector.current_template()
        tab = self._tab_manager.get_current_tab()
        base = os.path.dirname(tab.file_path) if tab and tab.file_path else None
        ExportDialog(self, md, tmpl, base).exec()

    def _show_settings(self):
        dlg = SettingsDialog(self)
        dlg.setWindowModality(Qt.ApplicationModal)
        if dlg.exec():
            self._tab_manager.apply_editor_settings(config_manager.config.get("editor", {}))
            self._apply_editor_state()
            self._base_title = tr("app_title")
            self.setWindowTitle(self._base_title)
            self._rebuild_menu()
            self._sync_menu_toggles()
            self._refresh_ui_text()

    def _rebuild_menu(self):
        self.menuBar().clear()
        self._init_menu()

    def _refresh_ui_text(self):
        self._template_label.setText(tr("template_label"))
        self._copy_wx_btn.setText(f"📋 {tr('btn_copy_wechat')}")
        self._copy_wx_btn.setToolTip(tr("tip_copy_wechat"))
        self._copy_img_btn.setText(f"🖼 {tr('btn_copy_image')}")
        self._copy_img_btn.setToolTip(tr("tip_copy_image"))
        self._export_btn.setText(f"📦 {tr('btn_export')}")
        self._export_btn.setToolTip(tr("tip_export"))
        self._preview_dock.setWindowTitle(tr("preview_tab"))
        self._ai_dock.setWindowTitle(tr("ai_tab"))
        self._outline_dock.setWindowTitle(tr("outline_title"))

    def _show_about(self):
        QMessageBox.about(self, tr("about_title"), tr("about_text"))

    def _zoom_in(self):
        if self._editor: self._editor.zoom_in()

    def _zoom_out(self):
        if self._editor: self._editor.zoom_out()

    def _zoom_reset(self):
        if self._editor: self._editor.reset_zoom()

    def _toggle_outline(self):
        v = not self._outline_dock.isVisible()
        self._outline_dock.setVisible(v)
        if v:
            self._outline.update_outline(self._editor.get_markdown() if self._editor else "")

    def _area_to_str(self, area) -> str:
        if area == Qt.LeftDockWidgetArea:
            return "left"
        elif area == Qt.RightDockWidgetArea:
            return "right"
        return "left"

    def _str_to_area(self, s: str):
        return Qt.RightDockWidgetArea if s == "right" else Qt.LeftDockWidgetArea

    def _apply_theme(self):
        theme = config_manager.get("theme", "light")
        if theme == "dark":
            app = QApplication.instance()
            app.setStyleSheet(DARK_STYLE)
        else:
            app = QApplication.instance()
            app.setStyleSheet(LIGHT_STYLE)

    def _toggle_theme(self):
        current = config_manager.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        config_manager.set("theme", new_theme)
        self._apply_theme()

    def _add_recent_file(self, path: str):
        files = config_manager.get("recent_files", [])
        if path in files:
            files.remove(path)
        files.insert(0, path)
        config_manager.set("recent_files", files[:10])
        self._update_recent_menu()

    def _update_recent_menu(self):
        self._recent_menu.clear()
        files = config_manager.get("recent_files", [])
        for f in files[:10]:
            if os.path.exists(f):
                self._recent_menu.addAction(
                    os.path.basename(f),
                    lambda p=f: self._open_recent(p)
                )

    def _open_recent(self, path: str):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                return
            self._tab_manager.add_tab(os.path.basename(path), content)
            self._tab_manager.set_tab_file_path(path)

    def _restore_dock_areas(self):
        ai_area = self._str_to_area(config_manager.get("window.ai_dock_area", "left"))
        self.addDockWidget(ai_area, self._ai_dock)
        pv_area = Qt.RightDockWidgetArea if ai_area == Qt.LeftDockWidgetArea else Qt.LeftDockWidgetArea
        self.addDockWidget(pv_area, self._preview_dock)

    def _swap_layout(self):
        """交换 AI 和预览的位置。"""
        ai_area = self.dockWidgetArea(self._ai_dock)
        new_ai = Qt.RightDockWidgetArea if ai_area == Qt.LeftDockWidgetArea else Qt.LeftDockWidgetArea
        new_pv = Qt.RightDockWidgetArea if new_ai == Qt.LeftDockWidgetArea else Qt.LeftDockWidgetArea
        self.addDockWidget(new_ai, self._ai_dock)
        self.addDockWidget(new_pv, self._preview_dock)

    def _reset_layout(self):
        """重置为默认布局：AI 左侧，预览右侧。"""
        self.addDockWidget(Qt.LeftDockWidgetArea, self._ai_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self._preview_dock)

    def _restore_geometry(self):
        w = config_manager.get("window.width", 1400)
        h = config_manager.get("window.height", 900)
        self.resize(min(w, 2560), min(h, 1440))
        self.move(max(0, config_manager.get("window.x", 100)),
                   max(0, config_manager.get("window.y", 100)))
        self.resizeDocks([self._ai_dock], [config_manager.get("window.ai_dock_width", 300)], Qt.Horizontal)
        self.resizeDocks([self._preview_dock], [config_manager.get("window.preview_dock_width", 450)], Qt.Horizontal)
        # 恢复 dock 区域
        self._restore_dock_areas()

    def _close_current_tab(self):
        idx = self._tab_manager.current_index()
        if idx >= 0:
            self._tab_manager._close_tab(idx)

    def _go_to_line(self):
        editor = self._editor
        if not editor:
            return
        from PySide6.QtWidgets import QInputDialog
        line, ok = QInputDialog.getInt(
            self, tr("find_title"), tr("go_to_line_label"),
            value=1, min=1, max=max(1, editor.document().blockCount())
        )
        if ok:
            editor.scroll_to_line(line)
            editor.setFocus()

    def _find_next(self):
        if hasattr(self, '_find_input') and self._find_input and self._find_input.text():
            self._do_find()

    def _find_previous(self):
        editor = self._editor
        if not editor or not hasattr(self, '_find_input') or not self._find_input or not self._find_input.text():
            return
        case = self._find_case.isChecked()
        whole = self._find_whole.isChecked()
        regex = self._find_regex.isChecked()
        editor.find_text_ext(self._find_input.text(), case_sensitive=case, whole_word=whole, regex=regex)

    def closeEvent(self, event):
        if self._tab_manager.has_unsaved_changes():
            reply = QMessageBox.warning(
                self, tr("unsaved_title"), tr("unsaved_msg"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return

        updates = {
            "window": {
                "width": self.width(),
                "height": self.height(),
                "x": self.x(),
                "y": self.y(),
            },
            "template": {"last_used": self._template_selector.current_template()},
            "outline_visible": self._outline_dock.isVisible(),
        }
        if self._ai_dock.isVisible():
            updates["window"]["ai_dock_width"] = self._ai_dock.width()
            updates["window"]["ai_dock_area"] = self._area_to_str(self.dockWidgetArea(self._ai_dock))
        if self._preview_dock.isVisible():
            updates["window"]["preview_dock_width"] = self._preview_dock.width()
        config_manager.update(updates)
        event.accept()

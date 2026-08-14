import re
import threading
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QScrollArea, QLabel, QFrame, QComboBox,
    QListWidget, QListWidgetItem, QMessageBox, QAbstractItemView,
    QLineEdit, QPlainTextEdit, QFileDialog, QInputDialog, QMenu,
)
from PySide6.QtGui import QFont

from core.i18n import tr
from core.ai_client import ai_client
from core import conversation_manager as cm
from core.prompt_manager import prompt_manager, Prompt


class ChatBubble(QFrame):
    insert_clicked = Signal(str)
    new_tab_clicked = Signal(str)
    copy_clicked = Signal(str)
    delete_clicked = Signal(object)
    regenerate_clicked = Signal(object)

    def __init__(self, text: str, is_user: bool, reasoning: str = "", parent=None):
        super().__init__(parent)
        self._text = text
        self._is_user = is_user
        self._reasoning = reasoning
        self._pending_display = ""
        self._conversation_index = -1
        self._is_action = False
        self._action_type = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 2)
        layout.setSpacing(4)

        self._display_timer = QTimer(self)
        self._display_timer.setSingleShot(True)
        self._display_timer.setInterval(60)
        self._display_timer.timeout.connect(self._apply_display)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        time_label = QLabel(datetime.now().strftime("%H:%M"))
        time_label.setStyleSheet("color:#aaa;font-size:10px;padding:0 4px;")

        self._delete_btn = QPushButton("×")
        self._delete_btn.setFixedSize(18, 18)
        self._delete_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #ccc; "
            "font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { color: #e53935; }"
        )
        self._delete_btn.setCursor(Qt.PointingHandCursor)
        self._delete_btn.setVisible(False)
        self._delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self))

        if is_user:
            top_row.addStretch()
            top_row.addWidget(time_label)
            top_row.addWidget(self._delete_btn)
        else:
            top_row.addWidget(time_label)
            top_row.addWidget(self._delete_btn)
            top_row.addStretch()
        layout.addLayout(top_row)

        self._reasoning_toggle = None
        self._reasoning_text = None
        if not is_user:
            self._setup_reasoning_section(layout)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.PlainText)
        self.label.setFont(QFont("Microsoft YaHei", 10))

        if is_user:
            bg, fg, bbl = "#e3f2fd", "#1565c0", "right"
        else:
            bg, fg, bbl = "#ffffff", "#333333", "left"

        self.label.setStyleSheet(
            f"QLabel {{ background-color: {bg}; color: {fg}; "
            f"border-radius: 10px; padding: 10px 14px; font-size: 13px; line-height: 1.6; "
            f"border: 1px solid #e8e8e8; "
            f"border-bottom-{bbl}-radius: 2px; }}"
        )

        wrapper = QHBoxLayout()
        if is_user:
            wrapper.addStretch()
        wrapper.addWidget(self.label)
        if not is_user:
            wrapper.addStretch()
        layout.addLayout(wrapper)

        if not is_user and text:
            self._setup_actions(layout)

        self._usage_label = None
        if not is_user:
            self._usage_label = QLabel()
            self._usage_label.setStyleSheet(
                "color:#aaa; font-size:10px; padding:2px 4px;"
            )
            self._usage_label.setAlignment(Qt.AlignRight)
            self._usage_label.setVisible(False)
            layout.addWidget(self._usage_label)

    def _setup_reasoning_section(self, parent_layout):
        self._reasoning_toggle = QPushButton(f"💭 {tr('ai_thinking_toggle')}")
        self._reasoning_toggle.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #9c27b0; "
            "font-size: 11px; padding: 2px 8px; text-align: left; }"
            "QPushButton:hover { color: #7b1fa2; text-decoration: underline; }"
        )
        self._reasoning_toggle.setCursor(Qt.PointingHandCursor)
        self._reasoning_toggle.setVisible(False)

        self._reasoning_text = QLabel()
        self._reasoning_text.setWordWrap(True)
        self._reasoning_text.setTextFormat(Qt.PlainText)
        self._reasoning_text.setFont(QFont("Microsoft YaHei", 9))
        self._reasoning_text.setStyleSheet(
            "QLabel { background-color: #faf5ff; color: #6b46c1; "
            "border-radius: 6px; padding: 8px 12px; "
            "border-left: 3px solid #9c27b0; "
            "margin: 2px 0; }"
        )
        self._reasoning_text.setVisible(False)

        self._reasoning_toggle.clicked.connect(self._toggle_reasoning)
        parent_layout.addWidget(self._reasoning_toggle)
        parent_layout.addWidget(self._reasoning_text)

    def _toggle_reasoning(self):
        if self._reasoning_text and self._reasoning_toggle:
            visible = not self._reasoning_text.isVisible()
            self._reasoning_text.setVisible(visible)
            self._reasoning_toggle.setText(
                f"💭 {tr('ai_thinking_toggle_open')}" if visible else f"💭 {tr('ai_thinking_toggle')}"
            )

    def set_text(self, text: str):
        self._text = text
        self._pending_display = text
        if not self._display_timer.isActive():
            self._display_timer.start()

    def _apply_display(self):
        if not self._pending_display:
            return
        self.label.setTextFormat(Qt.RichText)
        self.label.setText(self._render_markdown(self._pending_display))

    @staticmethod
    def _render_markdown(text: str) -> str:
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def code_block_replacer(m):
            lang = (m.group(1) or "").strip()
            code = m.group(2)
            header = f'<div style="font-size:10px;color:#888;padding:2px 12px;background:#eee;border-radius:4px 4px 0 0;border-left:3px solid #1a73e8;">{lang if lang else "code"}</div>'
            body = (
                f'<pre style="background:#f5f5f5;color:#333;padding:8px 12px;'
                f'border-radius:0 0 4px 4px;border-left:3px solid #1a73e8;'
                f'margin:0 0 8px 0;font-family:Consolas,monospace;font-size:12px;'
                f'white-space:pre-wrap;overflow-x:auto;">{code}</pre>'
            )
            return f'<div style="margin:4px 0;">{header}{body}</div>'

        text = re.sub(r'```(\w*)?\n(.+?)```', code_block_replacer, text, flags=re.DOTALL)

        text = text.replace("\n", "<br>")
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)\*(?!\*)', r'<em>\1</em>', text)
        text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
        text = re.sub(
            r'`([^`\n]+)`',
            r'<code style="background:#f0f0f0;color:#c7254e;padding:1px 4px;border-radius:2px;">\1</code>',
            text,
        )

        return f'<div style="white-space:pre-wrap;line-height:1.6;">{text}</div>'

    def append_reasoning(self, text: str):
        self._reasoning += text
        if self._reasoning_text and self._reasoning.strip():
            self._reasoning_text.setText(self._reasoning)
            self._reasoning_toggle.setVisible(True)
            if not self._reasoning_text.isVisible():
                self._reasoning_text.setVisible(True)
                self._reasoning_toggle.setText(f"💭 {tr('ai_thinking_toggle_open')}")

    def set_reasoning(self, reasoning: str):
        self._reasoning = reasoning
        if self._reasoning_text and reasoning.strip():
            self._reasoning_text.setText(reasoning)
            self._reasoning_toggle.setVisible(True)

    def has_code_blocks(self) -> bool:
        return bool(re.search(r'```(.+?)```', self._text, re.DOTALL))

    def _get_code_blocks(self) -> list:
        blocks = []
        for m in re.finditer(r'```(\w*)\n(.+?)```', self._text, re.DOTALL):
            blocks.append(m.group(2))
        if not blocks:
            for m in re.finditer(r'```(.+?)```', self._text, re.DOTALL):
                blocks.append(m.group(1))
        return blocks

    def set_usage(self, prompt_tokens: int, completion_tokens: int):
        if hasattr(self, "_usage_label") and self._usage_label:
            self._usage_label.setText(
                f"📊 {tr('usage_label', prompt=prompt_tokens, completion=completion_tokens)}"
            )
            self._usage_label.setVisible(True)

    def show_actions(self):
        if not self._is_user and self._text:
            lay = self.layout()
            if lay and not getattr(self, "_actions_added", False):
                self._setup_actions(lay)

    def enterEvent(self, event):
        self._delete_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._delete_btn.setVisible(False)
        super().leaveEvent(event)

    def _setup_actions(self, parent_layout):
        self._actions_added = True
        btn_style = (
            "QPushButton { background: transparent; border: 1px solid #e0e0e0;"
            "  border-radius: 3px; padding: 3px 10px; font-size: 11px; color: #888; }"
            "QPushButton:hover { background: #f0f0f0; color: #333; border-color: #bbb; }"
        )
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch()

        def _make_handler(signal):
            return lambda: signal.emit(self._text)

        def _make_code_handler(code_text):
            return lambda: self.copy_clicked.emit(code_text)

        def _make_regenerate_handler():
            return lambda: self.regenerate_clicked.emit(self)

        btn = QPushButton(f"🔄 {tr('ai_regenerate')}")
        btn.setStyleSheet(btn_style)
        btn.clicked.connect(_make_regenerate_handler())
        row.addWidget(btn)

        btn = QPushButton(tr("ai_insert"))
        btn.setStyleSheet(btn_style)
        btn.clicked.connect(_make_handler(self.insert_clicked))
        row.addWidget(btn)

        btn = QPushButton(tr("ai_new_tab"))
        btn.setStyleSheet(btn_style)
        btn.clicked.connect(_make_handler(self.new_tab_clicked))
        row.addWidget(btn)

        if self.has_code_blocks():
            code_text = "\n\n".join(self._get_code_blocks())
            btn = QPushButton(tr("ai_copy_code"))
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(_make_code_handler(code_text))
            row.addWidget(btn)

        btn = QPushButton(tr("ai_copy"))
        btn.setStyleSheet(btn_style)
        btn.clicked.connect(_make_handler(self.copy_clicked))
        row.addWidget(btn)

        parent_layout.addLayout(row)


class AIStreamWorker(QThread):
    chunk_received = Signal(str)
    reasoning_chunk = Signal(str)
    usage_received = Signal(int, int)
    finished = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, messages: list, parent=None):
        super().__init__(parent)
        self._messages = messages
        self._stopped = threading.Event()

    def stop(self):
        self._stopped.set()

    def run(self):
        try:
            gen = ai_client.chat(self._messages, stream=True)
            full = ""
            for item in gen:
                if self._stopped.is_set():
                    break
                if isinstance(item, str):
                    self.chunk_received.emit(item)
                    full += item
                elif isinstance(item, dict):
                    if "_usage" in item:
                        u = item["_usage"]
                        self.usage_received.emit(u.prompt_tokens, u.completion_tokens)
                        continue
                    rc = item.get("delta_reasoning", "")
                    dc = item.get("delta_content", "")
                    if rc:
                        self.reasoning_chunk.emit(rc)
                    if dc:
                        full += dc
                        self.chunk_received.emit(dc)
                else:
                    s = str(item)
                    self.chunk_received.emit(s)
                    full += s
            if not self._stopped.is_set():
                self.finished.emit(full)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AIPanel(QWidget):
    insert_requested = Signal(str)
    new_tab_requested = Signal(str)

    MAX_CONVERSATION_TURNS = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self._context_getter = None
        self._worker = None
        self._pending_bubble = None
        self._pending_content = ""
        self._pending_reasoning = ""
        self._conversation_messages: list = []
        self._current_conv_id: str = ""
        self._showing_history = False
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._pending_content_index = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_conversation_toolbar(layout)
        self._build_prompt_selector(layout)
        self._build_prompt_editor(layout)
        self._build_history_panel(layout)
        self._build_message_area(layout)
        self._build_context_preview(layout)
        self._build_token_summary(layout)
        self._build_input_area(layout)

        self._start_new_conversation()

    def _build_conversation_toolbar(self, parent):
        bar = QFrame()
        bar.setStyleSheet("QFrame { background: #f8f9fa; border-bottom: 1px solid #e0e0e0; }")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(6, 4, 6, 4)
        bl.setSpacing(4)

        self._new_chat_btn = QPushButton(f"+ {tr('ai_new_chat')}")
        self._new_chat_btn.setToolTip(tr("ai_tip_new_chat"))
        self._new_chat_btn.setStyleSheet(
            "QPushButton { background: #1a73e8; color: #fff; border: none; "
            "border-radius: 4px; padding: 5px 12px; font-size: 11px; font-weight: bold; }"
            "QPushButton:hover { background: #1557b0; }"
        )
        self._new_chat_btn.clicked.connect(self._start_new_conversation)

        self._history_btn = QPushButton(tr("ai_history"))
        self._history_btn.setToolTip(tr("ai_tip_history"))
        self._history_btn.setCheckable(True)
        self._history_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #d0d0d0; "
            "border-radius: 4px; padding: 5px 12px; font-size: 11px; color: #555; }"
            "QPushButton:hover { background: #e8e8e8; }"
            "QPushButton:checked { background: #e8f0fe; border-color: #1a73e8; color: #1a73e8; }"
        )
        self._history_btn.toggled.connect(self._toggle_history)

        self._export_btn = QPushButton(f"📥 {tr('ai_export')}")
        self._export_btn.setToolTip(tr("ai_tip_export"))
        self._export_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #d0d0d0; "
            "border-radius: 4px; padding: 5px 10px; font-size: 10px; color: #555; }"
            "QPushButton:hover { background: #e8e8e8; }"
        )
        self._export_btn.clicked.connect(self._export_conversation)

        self._delete_all_btn = QPushButton(tr("ai_delete_all"))
        self._delete_all_btn.setToolTip(tr("ai_tip_delete_all"))
        self._delete_all_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "font-size: 10px; color: #999; padding: 4px 8px; }"
            "QPushButton:hover { color: #e53935; }"
        )
        self._delete_all_btn.clicked.connect(self._delete_all_conversations)

        bl.addWidget(self._new_chat_btn)
        bl.addWidget(self._history_btn)
        bl.addStretch()
        bl.addWidget(self._export_btn)
        bl.addWidget(self._delete_all_btn)
        parent.addWidget(bar)

    def _build_prompt_selector(self, parent):
        row = QHBoxLayout()
        row.setContentsMargins(6, 2, 6, 2)

        self._prompt_combo = QComboBox()
        self._refresh_prompt_combo()
        self._prompt_combo.setStyleSheet(
            "QComboBox { background: #f5f5f5; border: 1px solid #e0e0e0; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px; color: #666; }"
            "QComboBox:hover { border-color: #bbb; }"
        )
        self._prompt_combo.currentIndexChanged.connect(self._on_prompt_index_changed)
        row.addWidget(self._prompt_combo, 1)

        self._manage_presets_btn = QPushButton(f"📂 {tr('ai_manage_presets')}")
        self._manage_presets_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #ddd; "
            "border-radius: 3px; padding: 3px 8px; font-size: 10px; color: #888; }"
            "QPushButton:hover { background: #e8e8e8; color: #333; }"
        )
        self._manage_presets_btn.clicked.connect(self._show_prompt_manager)
        row.addWidget(self._manage_presets_btn)
        parent.addLayout(row)

    def _refresh_prompt_combo(self):
        current_id = getattr(self, '_current_prompt_id', None)
        self._prompt_combo.blockSignals(True)
        self._prompt_combo.clear()
        all_prompts = prompt_manager.all()
        favorites = [p for p in all_prompts if p.is_favorite]
        others = [p for p in all_prompts if not p.is_favorite]
        fav_ids = {p.id for p in favorites}
        idx = 0
        selected_idx = 0
        for p in favorites:
            display = f"⭐ {p.name}" if p.is_favorite else p.name
            self._prompt_combo.addItem(display, p.id)
            if current_id and p.id == current_id:
                selected_idx = idx
            idx += 1
        if favorites and others:
            self._prompt_combo.insertSeparator(idx)
            idx += 1
        for p in others:
            self._prompt_combo.addItem(p.name, p.id)
            if current_id and p.id == current_id:
                selected_idx = idx
            idx += 1
        if not current_id and self._prompt_combo.count() > 0:
            first = prompt_manager.all()
            if first:
                for i in range(self._prompt_combo.count()):
                    if self._prompt_combo.itemData(i) == first[0].id:
                        selected_idx = i
                        break
        self._prompt_combo.setCurrentIndex(selected_idx)
        self._current_prompt_id = self._prompt_combo.currentData()
        self._prompt_combo.blockSignals(False)

    def _current_system_prompt(self) -> str:
        pid = self._prompt_combo.currentData()
        p = prompt_manager.get(pid) if pid else None
        if p:
            return p.render_system_prompt()
        all_p = prompt_manager.all()
        if all_p:
            return all_p[0].render_system_prompt()
        return ""

    def _on_prompt_index_changed(self, index: int):
        prev_id = getattr(self, '_current_prompt_id', None)
        self._current_prompt_id = self._prompt_combo.itemData(index)
        if self._conversation_messages and len(self._conversation_messages) > 1:
            reply = QMessageBox.question(
                self, tr("ai_confirm_switch_title"),
                tr("ai_confirm_switch_msg"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                self._current_prompt_id = prev_id
                self._prompt_combo.blockSignals(True)
                for i in range(self._prompt_combo.count()):
                    if self._prompt_combo.itemData(i) == prev_id:
                        self._prompt_combo.setCurrentIndex(i)
                        break
                self._prompt_combo.blockSignals(False)
                return
        self._on_prompt_changed()

    def _show_prompt_manager(self):
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget,
            QPushButton, QTextEdit, QLineEdit, QMessageBox, QLabel,
            QCheckBox, QComboBox, QGroupBox, QFileDialog as QFd,
            QWidget, QFormLayout,
        )
        from PySide6.QtCore import Qt

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("prompt_mgr_title"))
        dialog.setMinimumSize(780, 540)
        dialog.resize(820, 580)

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(6)

        # ── 顶部工具栏 ──
        toolbar = QHBoxLayout()

        self._pm_search = QLineEdit()
        self._pm_search.setPlaceholderText(f"🔍 {tr('prompt_mgr_search')}")
        self._pm_search.setStyleSheet(
            "QLineEdit { border: 1px solid #ddd; border-radius: 4px; "
            "padding: 4px 8px; font-size: 12px; }"
        )
        toolbar.addWidget(self._pm_search, 1)

        self._pm_cat_filter = QComboBox()
        self._pm_cat_filter.addItem(tr("prompt_mgr_all"))
        for cat in prompt_manager.get_categories():
            self._pm_cat_filter.addItem(cat)
        self._pm_cat_filter.setStyleSheet(
            "QComboBox { border: 1px solid #ddd; border-radius: 4px; "
            "padding: 4px 8px; font-size: 11px; }"
        )
        toolbar.addWidget(self._pm_cat_filter)

        self._pm_fav_only = QCheckBox(f"⭐ {tr('prompt_mgr_fav_only')}")
        self._pm_fav_only.setStyleSheet("font-size: 11px;")
        toolbar.addWidget(self._pm_fav_only)

        main_layout.addLayout(toolbar)

        # ── 搜索/过滤信号 ──
        def _refresh_pm_list():
            self._pm_refresh_list()

        self._pm_search.textChanged.connect(_refresh_pm_list)
        self._pm_cat_filter.currentTextChanged.connect(_refresh_pm_list)
        self._pm_fav_only.toggled.connect(_refresh_pm_list)

        # ── 分割面板 ──
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._pm_list = QListWidget()
        self._pm_list.setStyleSheet(
            "QListWidget { border: 1px solid #e0e0e0; border-radius: 4px; "
            "font-size: 12px; }"
            "QListWidget::item { padding: 6px 10px; border-bottom: 1px solid #f0f0f0; }"
            "QListWidget::item:hover { background: #e8f0fe; }"
            "QListWidget::item:selected { background: #d0e4f7; }"
        )
        left_layout.addWidget(self._pm_list, 1)

        left_buttons = QHBoxLayout()
        new_btn = QPushButton(f"➕ {tr('prompt_mgr_new')}")
        new_btn.setStyleSheet(
            "QPushButton { background: #1a73e8; color: #fff; border: none; "
            "border-radius: 3px; padding: 4px 12px; font-size: 11px; }"
            "QPushButton:hover { background: #1557b0; }"
        )
        new_btn.clicked.connect(lambda: self._pm_new_prompt(dialog))
        left_buttons.addWidget(new_btn)

        import_btn = QPushButton(f"📥 {tr('prompt_mgr_import')}")
        import_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #ddd; "
            "border-radius: 3px; padding: 4px 12px; font-size: 11px; color: #555; }"
            "QPushButton:hover { background: #e8e8e8; }"
        )
        import_btn.clicked.connect(lambda: self._pm_import(dialog))
        left_buttons.addWidget(import_btn)

        export_btn = QPushButton(f"📤 {tr('prompt_mgr_export')}")
        export_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #ddd; "
            "border-radius: 3px; padding: 4px 12px; font-size: 11px; color: #555; }"
            "QPushButton:hover { background: #e8e8e8; }"
        )
        export_btn.clicked.connect(lambda: self._pm_export(dialog))
        left_buttons.addWidget(export_btn)

        left_buttons.addStretch()
        left_layout.addLayout(left_buttons)

        splitter.addWidget(left_widget)

        # ── 右侧编辑面板 ──
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)

        form = QFormLayout()
        form.setSpacing(6)

        self._pm_name = QLineEdit()
        self._pm_name.setPlaceholderText(tr("prompt_mgr_name_ph"))
        form.addRow(tr("prompt_mgr_name_label"), self._pm_name)

        self._pm_category = QComboBox()
        self._pm_category.setEditable(True)
        self._pm_category.addItem("")
        for cat in prompt_manager.get_categories():
            self._pm_category.addItem(cat)
        form.addRow(tr("prompt_mgr_cat_label"), self._pm_category)

        self._pm_fav = QCheckBox(f"⭐ {tr('prompt_mgr_fav_only')}")
        form.addRow("", self._pm_fav)

        self._pm_desc = QLineEdit()
        self._pm_desc.setPlaceholderText(tr("prompt_mgr_desc_ph"))
        form.addRow(tr("prompt_mgr_desc_label"), self._pm_desc)

        right_layout.addLayout(form)

        self._pm_content = QPlainTextEdit()
        self._pm_content.setPlaceholderText(tr("prompt_mgr_content_ph"))
        self._pm_content.setFont(QFont("Consolas", 11))
        self._pm_content.setStyleSheet(
            "QPlainTextEdit { border: 1px solid #ddd; border-radius: 4px; "
            "padding: 6px; background: #fafafa; }"
        )
        right_layout.addWidget(QLabel(tr("prompt_mgr_content_label")), 0)
        right_layout.addWidget(self._pm_content, 1)

        # ── 搜索防抖 ──
        self._pm_search_timer = QTimer(self)
        self._pm_search_timer.setSingleShot(True)
        self._pm_search_timer.setInterval(200)
        self._pm_search_timer.timeout.connect(_refresh_pm_list)
        self._pm_search.textChanged.connect(lambda: self._pm_search_timer.start())

        # ── 角色卡 ──
        self._pm_char_group = QGroupBox(f"🎭 {tr('prompt_mgr_char_group')}")
        char_group = self._pm_char_group
        char_group.setCheckable(True)
        char_group.setChecked(False)
        char_group.setStyleSheet(
            "QGroupBox { font-size: 11px; color: #7c3aed; border: 1px solid #ddd; "
            "border-radius: 4px; margin-top: 8px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
        )
        char_layout = QFormLayout(char_group)

        self._pm_char_name = QLineEdit()
        self._pm_char_name.setPlaceholderText(tr("prompt_mgr_char_name_ph"))
        char_layout.addRow(tr("prompt_mgr_char_name_label"), self._pm_char_name)

        self._pm_char_icon = QLineEdit()
        self._pm_char_icon.setPlaceholderText("🎭")
        self._pm_char_icon.setMaxLength(4)
        char_layout.addRow(tr("prompt_mgr_char_icon_label"), self._pm_char_icon)

        self._pm_char_greeting = QTextEdit()
        self._pm_char_greeting.setPlaceholderText(tr("prompt_mgr_char_greeting_ph"))
        self._pm_char_greeting.setMaximumHeight(60)
        char_layout.addRow(tr("prompt_mgr_char_greeting_label"), self._pm_char_greeting)

        right_layout.addWidget(char_group)

        # ── 底部操作按钮 ──
        btn_row = QHBoxLayout()

        save_btn = QPushButton(f"💾 {tr('prompt_mgr_save')}")
        save_btn.setStyleSheet(
            "QPushButton { background: #1a73e8; color: #fff; border: none; "
            "border-radius: 4px; padding: 6px 20px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #1557b0; }"
        )
        save_btn.clicked.connect(lambda: self._pm_save(dialog))
        btn_row.addWidget(save_btn)

        self._pm_delete_btn = QPushButton(f"🗑 {tr('prompt_mgr_delete')}")
        self._pm_delete_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #e53935; "
            "border-radius: 4px; padding: 6px 20px; font-size: 12px; color: #e53935; }"
            "QPushButton:hover { background: #ffebee; }"
        )
        self._pm_delete_btn.clicked.connect(lambda: self._pm_delete(dialog))
        btn_row.addWidget(self._pm_delete_btn)

        btn_row.addStretch()

        close_btn = QPushButton(tr("prompt_mgr_close"))
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #ddd; "
            "border-radius: 4px; padding: 6px 20px; font-size: 12px; color: #888; }"
            "QPushButton:hover { color: #333; }"
        )
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(close_btn)

        right_layout.addLayout(btn_row)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 480])

        main_layout.addWidget(splitter, 1)

        # ── 列表选择信号 ──
        self._pm_selected_id = None
        self._pm_list.currentItemChanged.connect(lambda cur, prev: self._pm_on_select(cur))

        self._pm_refresh_list()
        if self._pm_list.count() > 0:
            self._pm_list.setCurrentRow(0)

        dialog.exec()

    def _pm_refresh_list(self):
        self._pm_list.blockSignals(True)
        self._pm_list.clear()
        query = self._pm_search.text().strip()
        cat = self._pm_cat_filter.currentText()
        fav_only = self._pm_fav_only.isChecked()

        prompts = prompt_manager.search(query) if query else prompt_manager.all()
        if cat and cat != tr("prompt_mgr_all"):
            prompts = [p for p in prompts if p.category == cat]
        if fav_only:
            prompts = [p for p in prompts if p.is_favorite]

        for p in prompts:
            fav = "⭐ " if p.is_favorite else ""
            cat_tag = f" [{p.category}]" if p.category else ""
            display = f"{fav}{p.name}{cat_tag}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, p.id)
            if p.is_builtin:
                item.setToolTip(f"{p.description}\n{tr('prompt_mgr_builtin_hint')}")
            else:
                item.setToolTip(p.description or "")
            if p.is_character:
                item.setIcon(self._char_icon(p.character_icon))
            self._pm_list.addItem(item)
        self._pm_list.blockSignals(False)

    @staticmethod
    def _char_icon(icon_text: str) -> "QIcon":
        from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
        pix = QPixmap(20, 20)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setFont(QFont("Segoe UI Emoji", 12))
        p.drawText(pix.rect(), Qt.AlignCenter, icon_text or "🎭")
        p.end()
        return QIcon(pix)

    def _pm_on_select(self, item):
        if not item:
            return
        pid = item.data(Qt.UserRole)
        if not pid:
            return
        p = prompt_manager.get(pid)
        if not p:
            return
        self._pm_selected_id = pid
        self._pm_name.setText(p.name)
        self._pm_name.setReadOnly(p.is_builtin)
        idx = self._pm_category.findText(p.category)
        if idx >= 0:
            self._pm_category.setCurrentIndex(idx)
        else:
            self._pm_category.setEditText(p.category)
        self._pm_category.setEnabled(not p.is_builtin)
        self._pm_fav.setChecked(p.is_favorite)
        self._pm_fav.setEnabled(not p.is_builtin)
        self._pm_desc.setText(p.description)
        self._pm_desc.setReadOnly(p.is_builtin)
        self._pm_content.setPlainText(p.content)
        self._pm_content.setReadOnly(p.is_builtin)
        self._pm_delete_btn.setEnabled(not p.is_builtin)
        if hasattr(self, '_pm_char_group') and self._pm_char_group:
            self._pm_char_group.setChecked(p.is_character)
            self._pm_char_group.setEnabled(not p.is_builtin)
            for child in self._pm_char_group.findChildren((QLineEdit, QTextEdit)):
                child.setEnabled(not p.is_builtin)
            self._pm_char_name.setText(p.character_name)
            self._pm_char_icon.setText(p.character_icon)
            self._pm_char_greeting.setPlainText(p.character_greeting)

    def _pm_new_prompt(self, dialog):
        p = prompt_manager.add(Prompt(name=tr("prompt_mgr_new_prompt"), content=""))
        self._current_prompt_id = p.id
        self._pm_refresh_list()
        self._refresh_prompt_combo()
        for i in range(self._pm_list.count()):
            item = self._pm_list.item(i)
            if item and item.data(Qt.UserRole) == p.id:
                self._pm_list.setCurrentItem(item)
                break

    def _pm_save(self, dialog):
        pid = self._pm_selected_id
        if not pid:
            return
        p = prompt_manager.get(pid)
        if not p or p.is_builtin:
            return
        name = self._pm_name.text().strip()
        content = self._pm_content.toPlainText().strip()
        if not name or not content:
            QMessageBox.warning(dialog, tr("prompt_mgr_title"), tr("prompt_mgr_empty_name_content"))
            return
        p.name = name
        p.content = content
        p.category = self._pm_category.currentText().strip()
        p.is_favorite = self._pm_fav.isChecked()
        p.description = self._pm_desc.text().strip()
        char_group = getattr(self, '_pm_char_group', None)
        if char_group and char_group.isChecked():
            p.is_character = True
            p.character_name = self._pm_char_name.text().strip()
            p.character_icon = self._pm_char_icon.text().strip() or "🎭"
            p.character_greeting = self._pm_char_greeting.toPlainText().strip()
        else:
            p.is_character = False
        prompt_manager.update(p)
        self._current_prompt_id = pid
        self._pm_refresh_list()
        self._refresh_prompt_combo()

    def _pm_delete(self, dialog):
        pid = self._pm_selected_id
        if not pid:
            return
        p = prompt_manager.get(pid)
        if not p or p.is_builtin:
            return
        reply = QMessageBox.question(
            dialog, tr("prompt_mgr_title"), tr("prompt_mgr_delete_confirm").format(name=p.name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        prompt_manager.delete(pid)
        self._pm_selected_id = None
        self._current_prompt_id = None
        self._pm_refresh_list()
        self._refresh_prompt_combo()
        if self._pm_list.count() > 0:
            self._pm_list.setCurrentRow(0)

    def _pm_import(self, dialog):
        path, _ = QFileDialog.getOpenFileName(
            dialog, tr("prompt_mgr_import_title"), "", "JSON (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            count = prompt_manager.import_json(path)
            QMessageBox.information(dialog, tr("prompt_mgr_import_success"), tr("prompt_mgr_import_success_msg").format(count=count))
            self._current_prompt_id = None
            self._pm_refresh_list()
            self._refresh_prompt_combo()
            self._pm_cat_filter.clear()
            self._pm_cat_filter.addItem(tr("prompt_mgr_all"))
            for cat in prompt_manager.get_categories():
                self._pm_cat_filter.addItem(cat)
        except Exception as e:
            QMessageBox.warning(dialog, tr("prompt_mgr_import_failed"), str(e))

    def _pm_export(self, dialog):
        pid = self._pm_selected_id
        if not pid:
            QMessageBox.information(dialog, tr("prompt_mgr_title"), tr("prompt_mgr_select_first"))
            return
        path, _ = QFileDialog.getSaveFileName(
            dialog, tr("prompt_mgr_export_title"), "", "JSON (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            prompt_manager.export_json([pid], path)
            QMessageBox.information(dialog, tr("prompt_mgr_export_success"), tr("prompt_mgr_export_success_msg").format(path=path))
        except Exception as e:
            QMessageBox.warning(dialog, tr("prompt_mgr_export_failed"), str(e))

    def _build_prompt_editor(self, parent):
        self._prompt_edit_frame = QFrame()
        self._prompt_edit_frame.setStyleSheet(
            "QFrame { background: #fafafe; border-bottom: 1px solid #e8e8e8; }"
        )
        pel = QVBoxLayout(self._prompt_edit_frame)
        pel.setContentsMargins(8, 4, 8, 4)
        pel.setSpacing(4)

        header = QHBoxLayout()
        toggle_btn = QPushButton(f"📝 {tr('ai_edit_prompt')}")
        toggle_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "font-size: 10px; color: #888; padding: 2px 4px; text-align: left; }"
            "QPushButton:hover { color: #333; }"
        )
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.setCheckable(True)
        header.addWidget(toggle_btn)
        header.addStretch()
        pel.addLayout(header)

        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setPlaceholderText(tr("ai_prompt_placeholder"))
        self._prompt_edit.setMaximumHeight(100)
        self._prompt_edit.setFont(QFont("Microsoft YaHei", 10))
        self._prompt_edit.setStyleSheet(
            "QPlainTextEdit { border: 1px solid #ddd; border-radius: 4px; "
            "padding: 6px; background: #fff; color: #333; }"
        )
        self._prompt_edit.setVisible(False)
        pel.addWidget(self._prompt_edit)

        self._prompt_btn_container = QWidget()
        btn_row = QHBoxLayout(self._prompt_btn_container)
        btn_row.setContentsMargins(0, 0, 0, 0)

        save_prompt_btn = QPushButton(tr("ai_apply"))
        save_prompt_btn.setStyleSheet(
            "QPushButton { background: #1a73e8; color: #fff; border: none; "
            "border-radius: 3px; padding: 3px 12px; font-size: 10px; }"
            "QPushButton:hover { background: #1557b0; }"
        )
        save_prompt_btn.clicked.connect(self._apply_system_prompt_edit)

        cancel_prompt_btn = QPushButton(tr("ai_cancel"))
        cancel_prompt_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #ddd; "
            "border-radius: 3px; padding: 3px 12px; font-size: 10px; color: #888; }"
            "QPushButton:hover { color: #333; }"
        )
        cancel_prompt_btn.clicked.connect(lambda: self._prompt_edit.setVisible(False))

        btn_row.addStretch()
        btn_row.addWidget(save_prompt_btn)
        btn_row.addWidget(cancel_prompt_btn)
        self._prompt_btn_container.setVisible(False)
        pel.addWidget(self._prompt_btn_container)

        toggle_btn.toggled.connect(self._toggle_prompt_editor)
        parent.addWidget(self._prompt_edit_frame)

    def _toggle_prompt_editor(self, checked: bool):
        self._prompt_edit.setVisible(checked)
        self._prompt_btn_container.setVisible(checked)
        if checked:
            current = self._current_system_prompt()
            self._prompt_edit.setPlainText(current)
            self._prompt_edit.setFocus()

    def _apply_system_prompt_edit(self):
        text = self._prompt_edit.toPlainText().strip()
        if not text:
            return
        if self._conversation_messages and self._conversation_messages[0]["role"] == "system":
            self._conversation_messages[0]["content"] = text
        else:
            self._conversation_messages.insert(0, {"role": "system", "content": text})
        self._save_current_conversation()
        self._prompt_edit.setVisible(False)

    def _build_history_panel(self, parent):
        self._history_search = QLineEdit()
        self._history_search.setPlaceholderText(f"🔍 {tr('ai_search_history')}")
        self._history_search.setStyleSheet(
            "QLineEdit { border: none; border-bottom: 1px solid #e0e0e0; "
            "padding: 6px 10px; font-size: 11px; background: #fafafa; color: #888; }"
        )
        self._history_search.setVisible(False)
        self._history_search.textChanged.connect(self._filter_history)
        parent.addWidget(self._history_search)

        self._history_list = QListWidget()
        self._history_list.setStyleSheet(
            "QListWidget { border: none; background: #fafafa; padding: 4px; }"
            "QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #eee; "
            "border-radius: 4px; }"
            "QListWidget::item:hover { background: #e8f0fe; }"
            "QListWidget::item:selected { background: #d0e4f7; }"
        )
        self._history_list.setVisible(False)
        self._history_list.itemClicked.connect(self._on_history_item_clicked)
        self._history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_list.customContextMenuRequested.connect(self._on_history_context_menu)
        parent.addWidget(self._history_list)

    def _build_message_area(self, parent):
        self._welcome = QFrame()
        wl = QVBoxLayout(self._welcome)
        wl.setContentsMargins(16, 20, 16, 20)
        t = QLabel(tr("ai_welcome_title"))
        t.setFont(QFont("Microsoft YaHei", 14))
        t.setAlignment(Qt.AlignCenter)
        wl.addWidget(t)
        d = QLabel(tr("ai_welcome_desc"))
        d.setFont(QFont("Microsoft YaHei", 10))
        d.setStyleSheet("color:#999;padding-top:8px;")
        d.setAlignment(Qt.AlignCenter)
        d.setWordWrap(True)
        wl.addWidget(d)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._msg_container = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setAlignment(Qt.AlignTop)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_container)

        self._chat_stack = QFrame()
        cs = QVBoxLayout(self._chat_stack)
        cs.setContentsMargins(0, 0, 0, 0)
        cs.addWidget(self._welcome)
        cs.addWidget(self._scroll, 1)
        parent.addWidget(self._chat_stack, 1)

    def _build_context_preview(self, parent):
        self._context_label = QLabel()
        self._context_label.setStyleSheet(
            "QLabel { color: #9c27b0; font-size: 10px; padding: 2px 12px; "
            "background: #faf5ff; border-bottom: 1px solid #e8d5f0; }"
        )
        self._context_label.setVisible(False)
        parent.addWidget(self._context_label)

    def _update_context_preview(self):
        if not self._context_getter:
            self._context_label.setVisible(False)
            return
        ctx = self._context_getter()
        if ctx:
            chars = len(ctx)
            preview = ctx[:60].replace("\n", " ")
            self._context_label.setText(f"📎 已选中 {chars} 字符: \"{preview}{'…' if chars > 60 else ''}\"")
            self._context_label.setVisible(True)
        else:
            self._context_label.setVisible(False)

    def _build_token_summary(self, parent):
        self._token_summary_label = QLabel()
        self._token_summary_label.setStyleSheet(
            "QLabel { color: #aaa; font-size: 10px; padding: 2px 12px; "
            "background: #fafafa; border-top: 1px solid #f0f0f0; }"
        )
        self._token_summary_label.setVisible(False)
        parent.addWidget(self._token_summary_label)

    def _build_input_area(self, parent):
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.StyledPanel)
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(8, 6, 8, 6)
        il.setSpacing(6)

        self._input = QTextEdit()
        self._input.setPlaceholderText(tr("ai_input_placeholder"))
        self._input.setMaximumHeight(80)
        self._input.setAcceptRichText(False)
        self._input.setFont(QFont("Microsoft YaHei", 11))
        self._input.installEventFilter(self)
        il.addWidget(self._input)

        bl = QVBoxLayout()
        bl.setSpacing(2)

        self._send_btn = QPushButton(tr("ai_send"))
        self._send_btn.setToolTip(tr("ai_tip_send"))
        self._send_btn.setFixedSize(52, 32)
        self._send_btn.clicked.connect(self._send)
        self._send_btn.setStyleSheet(
            "QPushButton{background:#1a73e8;color:#fff;border:none;border-radius:4px;font-size:11px;}"
            "QPushButton:hover{background:#1557b0;}")
        bl.addWidget(self._send_btn)

        self._stop_btn = QPushButton(f"■ {tr('ai_stop')}")
        self._stop_btn.setToolTip(tr("ai_tip_stop"))
        self._stop_btn.setFixedSize(52, 32)
        self._stop_btn.setVisible(False)
        self._stop_btn.clicked.connect(self._stop_generation)
        self._stop_btn.setStyleSheet(
            "QPushButton{background:#e53935;color:#fff;border:none;border-radius:4px;font-size:10px;font-weight:bold;}"
            "QPushButton:hover{background:#c62828;}")
        bl.addWidget(self._stop_btn)

        self._clear_btn = QPushButton(tr("ai_clear"))
        self._clear_btn.setToolTip(tr("ai_tip_clear"))
        self._clear_btn.setFixedSize(52, 22)
        self._clear_btn.clicked.connect(lambda: self._clear() if self._confirm_clear() else None)
        self._clear_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#999;border:none;font-size:10px;}"
            "QPushButton:hover{color:#666;}")
        bl.addWidget(self._clear_btn)
        il.addLayout(bl)
        parent.addWidget(input_frame)

    # ── 对话管理 ──

    def _start_new_conversation(self):
        if not self._confirm_clear():
            return
        self._clear()
        self._current_conv_id = cm.new_id()
        self._history_btn.setChecked(False)
        self._history_list.setVisible(False)

    def _toggle_history(self, checked: bool):
        self._showing_history = checked
        if checked:
            self._refresh_history_list()
            self._history_search.clear()
        self._history_search.setVisible(checked)
        self._history_list.setVisible(checked)
        self._chat_stack.setVisible(not checked)

    def _filter_history(self, text: str):
        for i in range(self._history_list.count()):
            item = self._history_list.item(i)
            if item:
                item.setHidden(text and text.lower() not in item.text().lower())

    def _refresh_history_list(self):
        self._history_list.clear()
        convs = cm.list_conversations()
        if not convs:
            item = QListWidgetItem(tr("ai_no_history"))
            item.setFlags(Qt.NoItemFlags)
            self._history_list.addItem(item)
            return
        for c in convs:
            title = c.get("title", tr("ai_unnamed"))
            ts = datetime.fromtimestamp(c.get("created_at", 0)).strftime("%m/%d %H:%M")
            msg_count = c.get("message_count", 0)
            display = f"{title}\n{ts} · {tr('ai_message_count').format(count=msg_count)}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, c["id"])
            self._history_list.addItem(item)

    def _on_history_item_clicked(self, item: QListWidgetItem):
        conv_id = item.data(Qt.UserRole)
        if not conv_id:
            return
        messages = cm.load_conversation(conv_id)
        if messages is None:
            return
        if not self._confirm_clear():
            return
        self._current_conv_id = conv_id
        self._load_messages(messages)
        self._history_btn.setChecked(False)
        self._input.setFocus()

    def _on_history_context_menu(self, pos):
        item = self._history_list.itemAt(pos)
        if not item or not item.data(Qt.UserRole):
            return
        conv_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        rename_action = menu.addAction(tr("ai_rename"))
        delete_action = menu.addAction(tr("ai_delete"))
        action = menu.exec(self._history_list.mapToGlobal(pos))
        if action == rename_action:
            new_name, ok = QInputDialog.getText(
                self, tr("ai_rename_title"), tr("ai_rename_label"),
                QLineEdit.Normal, item.text()
            )
            if ok and new_name:
                cm.rename_conversation(conv_id, new_name)
                self._refresh_history_list()
        elif action == delete_action:
            reply = QMessageBox.question(
                self, tr("ai_delete_conv_title"), tr("ai_delete_conv_msg"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                cm.delete_conversation(conv_id)
                self._refresh_history_list()
                if conv_id == self._current_conv_id:
                    self._start_new_conversation()

    def _delete_all_conversations(self):
        reply = QMessageBox.question(
            self, tr("ai_delete_all_title"), tr("ai_delete_all_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            cm.delete_all()
            self._refresh_history_list()
            self._start_new_conversation()

    def _save_current_conversation(self):
        if not self._current_conv_id or not self._conversation_messages:
            return
        title = ""
        if self._conversation_messages:
            for m in self._conversation_messages:
                if m.get("role") == "user":
                    title = m["content"][:40]
                    break
        messages_to_save = []
        for m in self._conversation_messages:
            messages_to_save.append({"role": m["role"], "content": m.get("content", "")})
        cm.save_conversation(self._current_conv_id, messages_to_save, title)

    def _load_messages(self, messages: list):
        self._clear()
        self._conversation_messages = list(messages)
        for idx, m in enumerate(messages):
            if m["role"] == "system":
                continue
            self._add_bubble(m["content"], m["role"] == "user", conversation_index=idx)
        if self._msg_layout.count() > 1:
            self._welcome.setVisible(False)
        self._scroll_bottom()

    # ── 事件 ──

    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key_Escape:
                if self._worker and self._worker.isRunning():
                    self._stop_generation()
                    return True
            if obj is self._input:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers():
                    self._send()
                    return True
        elif event.type() == event.Type.FocusIn and obj is self._input:
            self._update_context_preview()
        return super().eventFilter(obj, event)

    def set_context_getter(self, getter):
        self._context_getter = getter

    def _ensure_visible(self):
        self._welcome.setVisible(False)
        self._scroll.setVisible(True)
        self._history_list.setVisible(False)
        self._history_btn.setChecked(False)
        self._chat_stack.setVisible(True)

    AI_ACTION_PROMPTS = {
        "continue_writing": "你是一个专业写作助手。根据用户提供的文本，续写后续内容，保持风格和语气一致。直接输出续写内容，不要解释。",
        "polish": "你是一个专业文字润色专家。优化用户提供的文本，使其更流畅、专业、有表现力。保持原意不变。直接返回润色结果，不要解释。",
        "translate": "你是一个专业翻译。将用户文本翻译为另一种语言（自动检测源语言）。保留 Markdown 格式。直接返回译文，如有必要可在译文后加简短注释。",
        "summarize": "你是一个专业摘要助手。将用户提供的文本提炼为精炼摘要，控制原文 1/5 以内。提取核心观点。直接输出摘要。",
    }

    def execute_action(self, action_type: str, selected_text: str, full_document: str):
        if self._worker and self._worker.isRunning():
            return
        default_prompt = prompt_manager.all()[0].render_system_prompt() if prompt_manager.all() else ""
        system_prompt = self.AI_ACTION_PROMPTS.get(action_type, default_prompt)
        messages = [{"role": "system", "content": system_prompt}]
        if action_type == "summarize" and not selected_text:
            messages.append({"role": "user", "content": f"请为以下全文生成摘要：\n\n{full_document}"})
        elif selected_text:
            messages.append({"role": "user", "content": selected_text})
        else:
            messages.append({"role": "user", "content": full_document})

        self._ensure_visible()

        action_labels = {
            "continue_writing": "✍ 续写", "polish": "✨ 润色",
            "translate": "🌐 翻译", "summarize": "📋 摘要",
        }
        label = action_labels.get(action_type, action_type)

        user_content = messages[-1]["content"] if messages else ""
        self._conversation_messages.append({"role": "user", "content": f"**[{label}]**\n\n{user_content}"})
        user_idx = len(self._conversation_messages) - 1

        bubble = ChatBubble("", False)
        bubble._conversation_index = -1
        bubble._is_action = True
        bubble._action_type = action_type
        bubble.set_text(f"**[{label}]**\n\n⏳ {tr('loading')}")
        bubble.insert_clicked.connect(self._on_insert)
        bubble.new_tab_clicked.connect(self._on_new_tab)
        bubble.copy_clicked.connect(self._on_copy)
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, bubble)
        self._scroll_bottom()

        self._pending_bubble = bubble
        self._pending_content = ""
        self._pending_reasoning = ""
        self._worker = AIStreamWorker(messages)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.reasoning_chunk.connect(self._on_reasoning_chunk)
        self._worker.usage_received.connect(self._on_usage)
        self._worker.finished.connect(self._on_action_finished)
        self._worker.error_occurred.connect(self._on_action_error)
        self._worker.start()

    def _on_action_finished(self, full: str):
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)
        self._input.setEnabled(True)
        self._clear_btn.setEnabled(True)
        if self._pending_bubble:
            if self._pending_content:
                text = self._pending_content
                at = getattr(self._pending_bubble, '_action_type', '')
                labels = {"continue_writing": "✍ 续写结果", "polish": "✨ 润色结果",
                           "translate": "🌐 翻译结果", "summarize": "📋 摘要"}
                label = labels.get(at, "AI 结果")
                self._pending_bubble.set_text(f"**[{label}]**\n\n{text}")
                idx = len(self._conversation_messages)
                self._pending_bubble._conversation_index = idx
                self._conversation_messages.append({"role": "assistant", "content": f"**[{label}]**\n\n{text}"})
                self._save_current_conversation()
            if self._pending_reasoning:
                self._pending_bubble.set_reasoning(self._pending_reasoning)
            self._pending_bubble.show_actions()
        self._pending_bubble = None
        self._pending_content = ""
        self._pending_reasoning = ""

    def _on_action_error(self, err: str):
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)
        self._input.setEnabled(True)
        self._clear_btn.setEnabled(True)
        if self._pending_bubble:
            self._pending_bubble.set_text(f"**{tr('error_title')}:** {err}")
        self._pending_bubble = None
        self._pending_content = ""

    def _regenerate(self, bubble):
        if self._worker and self._worker.isRunning():
            return
        idx = bubble._conversation_index
        if idx < 0 or idx >= len(self._conversation_messages):
            return
        if self._conversation_messages[idx]["role"] != "assistant":
            return

        self._conversation_messages.pop(idx)
        insert_pos = self._msg_layout.indexOf(bubble)
        if insert_pos >= 0:
            self._msg_layout.removeWidget(bubble)
        bubble.deleteLater()

        api_messages = []
        for m in self._conversation_messages:
            clean = {"role": m.get("role", "user"), "content": m.get("content", "")}
            api_messages.append(clean)

        self._pending_content = ""
        self._pending_reasoning = ""

        self._pending_bubble = ChatBubble("", False)
        self._pending_bubble._conversation_index = idx
        self._pending_bubble.insert_clicked.connect(self._on_insert)
        self._pending_bubble.new_tab_clicked.connect(self._on_new_tab)
        self._pending_bubble.copy_clicked.connect(self._on_copy)
        self._pending_bubble.delete_clicked.connect(self._delete_message)
        self._pending_bubble.regenerate_clicked.connect(self._regenerate)

        if insert_pos >= 0:
            self._msg_layout.insertWidget(insert_pos, self._pending_bubble)
        else:
            self._msg_layout.insertWidget(self._msg_layout.count() - 1, self._pending_bubble)

        self._send_btn.setVisible(False)
        self._stop_btn.setVisible(True)
        self._input.setEnabled(False)

        self._worker = AIStreamWorker(api_messages)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.reasoning_chunk.connect(self._on_reasoning_chunk)
        self._worker.usage_received.connect(self._on_usage)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _scroll_bottom(self):
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )

    def _truncate_history(self):
        if len(self._conversation_messages) <= self.MAX_CONVERSATION_TURNS * 2 + 1:
            return
        system = self._conversation_messages[0] if self._conversation_messages and self._conversation_messages[0]["role"] == "system" else None
        keep = self._conversation_messages[-(self.MAX_CONVERSATION_TURNS * 2):]
        if system:
            keep.insert(0, system)
        self._conversation_messages = keep

    def _clear(self):
        self._stop_generation()
        while self._msg_layout.count() > 0:
            item = self._msg_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._msg_layout.addStretch()
        self._welcome.setVisible(True)
        self._conversation_messages = []
        self._pending_bubble = None
        self._pending_content = ""
        self._pending_reasoning = ""
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._token_summary_label.setVisible(False)

    def _confirm_clear(self) -> bool:
        if self._conversation_messages and len(self._conversation_messages) > 1:
            reply = QMessageBox.question(
                self, tr("ai_confirm_clear_title"),
                tr("ai_confirm_clear_msg"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            return reply == QMessageBox.Yes
        return True

    def _on_prompt_changed(self):
        self._clear()

    def _send(self):
        text = self._input.toPlainText().strip()
        if not text or (self._worker and self._worker.isRunning()):
            return
        self._welcome.setVisible(False)
        self._input.clear()

        if not ai_client.available:
            self._add_bubble(tr("ai_not_configured"), False)
            return

        if not self._conversation_messages:
            self._conversation_messages.append(
                {"role": "system", "content": self._current_system_prompt()}
            )

        user_content = text
        if self._context_getter:
            ctx = self._context_getter()
            if ctx:
                user_content = (
                    f"用户选中了以下内容：\n###\n{ctx}\n###\n\n"
                    f"基于以上选中内容回答：{text}"
                )

        self._update_context_preview()
        self._conversation_messages.append({"role": "user", "content": user_content})
        self._truncate_history()

        api_messages = []
        for m in self._conversation_messages:
            clean = {"role": m.get("role", "user"), "content": m.get("content", "")}
            api_messages.append(clean)

        user_idx = len(self._conversation_messages) - 1
        self._add_bubble(text, True, conversation_index=user_idx)
        self._pending_content = ""
        self._pending_reasoning = ""

        self._pending_content_index = len(self._conversation_messages)
        self._pending_bubble = ChatBubble("", False)
        self._pending_bubble._conversation_index = self._pending_content_index
        self._pending_bubble.insert_clicked.connect(self._on_insert)
        self._pending_bubble.new_tab_clicked.connect(self._on_new_tab)
        self._pending_bubble.copy_clicked.connect(self._on_copy)
        self._pending_bubble.delete_clicked.connect(self._delete_message)
        self._pending_bubble.regenerate_clicked.connect(self._regenerate)
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, self._pending_bubble)

        self._send_btn.setVisible(False)
        self._stop_btn.setVisible(True)
        self._input.setEnabled(False)
        self._clear_btn.setEnabled(False)

        self._worker = AIStreamWorker(api_messages)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.reasoning_chunk.connect(self._on_reasoning_chunk)
        self._worker.usage_received.connect(self._on_usage)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_chunk(self, text: str):
        self._pending_content += text
        if self._pending_bubble:
            self._pending_bubble.set_text(self._pending_content)
        self._scroll_bottom()

    def _on_reasoning_chunk(self, text: str):
        self._pending_reasoning += text
        if self._pending_bubble:
            self._pending_bubble.append_reasoning(text)

    def _on_usage(self, prompt_tokens: int, completion_tokens: int):
        if self._pending_bubble:
            self._pending_bubble.set_usage(prompt_tokens, completion_tokens)
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        total = self._total_prompt_tokens + self._total_completion_tokens
        self._token_summary_label.setText(
            f"📊 {tr('usage_summary', prompt=self._total_prompt_tokens, completion=self._total_completion_tokens, total=total)}"
        )
        self._token_summary_label.setVisible(True)

    def _on_finished(self, full: str):
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)
        self._input.setEnabled(True)
        self._input.setFocus()
        self._clear_btn.setEnabled(True)
        if self._pending_bubble:
            if self._pending_content:
                self._pending_bubble.set_text(self._pending_content)
            if self._pending_reasoning:
                self._pending_bubble.set_reasoning(self._pending_reasoning)
            self._pending_bubble.show_actions()
        if full:
            insert_idx = self._pending_bubble._conversation_index if self._pending_bubble else -1
            if 0 <= insert_idx <= len(self._conversation_messages):
                self._conversation_messages.insert(insert_idx, {"role": "assistant", "content": full})
            else:
                self._conversation_messages.append(
                    {"role": "assistant", "content": full}
                )
        self._pending_bubble = None
        self._pending_content = ""
        self._pending_reasoning = ""
        self._save_current_conversation()

    def _on_error(self, err: str):
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)
        self._input.setEnabled(True)
        self._clear_btn.setEnabled(True)
        if self._pending_bubble:
            self._pending_bubble.set_text(f"**{tr('error_title')}:** {err}")
        else:
            self._add_bubble(f"{tr('error_title')}: {err}", False)
        if self._conversation_messages and self._conversation_messages[-1]["role"] == "user":
            self._conversation_messages.pop()
        self._pending_bubble = None
        self._pending_content = ""

    def _delete_message(self, bubble):
        idx = bubble._conversation_index
        if idx < 0 or idx >= len(self._conversation_messages):
            bubble.deleteLater()
            return
        role = self._conversation_messages[idx]["role"]
        indices_to_remove = {idx}
        if role == "user" and idx + 1 < len(self._conversation_messages):
            indices_to_remove.add(idx + 1)
        elif role == "assistant" and idx - 1 >= 0:
            indices_to_remove.add(idx - 1)
        for i in sorted(indices_to_remove, reverse=True):
            self._conversation_messages.pop(i)
        bubble.deleteLater()
        self._rebuild_bubble_indices()
        self._save_current_conversation()

    def _rebuild_bubble_indices(self):
        conv_idx = 1 if (self._conversation_messages and self._conversation_messages[0].get("role") == "system") else 0
        for i in range(self._msg_layout.count()):
            item = self._msg_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ChatBubble):
                if conv_idx < len(self._conversation_messages):
                    item.widget()._conversation_index = conv_idx
                else:
                    item.widget()._conversation_index = -1
                conv_idx += 1
        if self._msg_layout.count() <= 1:
            self._welcome.setVisible(True)

    def _on_insert(self, text: str): self.insert_requested.emit(text)

    def _on_new_tab(self, text: str): self.new_tab_requested.emit(text)

    def _on_copy(self, text: str):
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            QApplication.clipboard().setText(text)

    def _export_conversation(self):
        if not self._conversation_messages:
            QMessageBox.information(self, tr("conv_export_title"), tr("conv_export_empty"))
            return
        from pathlib import Path
        path, selected_filter = QFileDialog.getSaveFileName(
            self, tr("conv_export_title"), str(Path.home() / tr("conv_export_filename")),
            "Markdown (*.md);;JSON (*.json)"
        )
        if not path:
            return
        if path.endswith(".json"):
            import json
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self._conversation_messages, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, tr("export_success"), tr("conv_export_success").format(path=path))
            except Exception as e:
                QMessageBox.warning(self, tr("conv_export_fail"), str(e))
            return
        lines = ["# AI 对话记录\n"]
        for m in self._conversation_messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "system":
                lines.append(f"> **系统提示词:**\n>\n> {content.replace(chr(10), chr(10) + '> ')}\n")
            elif role == "user":
                lines.append(f"## 用户\n\n{content}\n")
            elif role == "assistant":
                lines.append(f"## AI 助手\n\n{content}\n")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            QMessageBox.information(self, tr("export_success"), tr("conv_export_success").format(path=path))
        except Exception as e:
            QMessageBox.warning(self, tr("conv_export_fail"), str(e))

    def _stop_generation(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.quit()
            self._worker.wait(1000)
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)
        self._input.setEnabled(True)
        self._input.setFocus()
        self._clear_btn.setEnabled(True)
        if self._pending_bubble:
            if self._pending_content:
                self._pending_bubble.set_text(self._pending_content + f"\n\n*{tr('ai_stopped')}*")
                insert_idx = self._pending_bubble._conversation_index
                if 0 <= insert_idx <= len(self._conversation_messages):
                    self._conversation_messages.insert(insert_idx, {"role": "assistant", "content": self._pending_content})
                else:
                    self._conversation_messages.append({"role": "assistant", "content": self._pending_content})
                self._save_current_conversation()
            self._pending_bubble.show_actions()
        self._pending_bubble = None
        self._pending_content = ""
        self._pending_reasoning = ""

    def stop(self):
        self._stop_generation()

    def _add_bubble(self, text: str, is_user: bool, conversation_index: int = -1):
        bubble = ChatBubble(text, is_user)
        bubble._conversation_index = conversation_index
        bubble.delete_clicked.connect(self._delete_message)
        if not is_user:
            bubble.insert_clicked.connect(self._on_insert)
            bubble.new_tab_clicked.connect(self._on_new_tab)
            bubble.copy_clicked.connect(self._on_copy)
            bubble.regenerate_clicked.connect(self._regenerate)
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, bubble)
        self._scroll_bottom()

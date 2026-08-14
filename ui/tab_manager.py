import os

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabBar, QStackedWidget, QMessageBox, QMenu, QApplication,
)

from core.i18n import tr
from ui.editor import Editor


class EditorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.editor = Editor()
        layout.addWidget(self.editor)
        self.editor.document().setModified(False)

        self.file_path = None
        self._title = tr("untitled")

    @property
    def title(self):
        return os.path.basename(self.file_path) if self.file_path else self._title

    def is_modified(self):
        return self.editor.document().isModified()

    def set_plain_text(self, text: str):
        self.editor.setPlainText(text)


class TabManager(QWidget):
    editor_changed = Signal(object)
    tab_closed = Signal(object)
    file_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_bar = QTabBar()
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setMovable(True)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setDocumentMode(True)
        self._tab_bar.setElideMode(Qt.ElideRight)
        self._tab_bar.setStyleSheet(
            "QTabBar::tab { min-height: 28px; padding: 2px 14px; }"
            "QTabBar::close-button { width: 16px; height: 16px; margin: 2px; }"
        )
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        self._tab_bar.tabCloseRequested.connect(self._close_tab)
        self._tab_bar.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tab_bar.customContextMenuRequested.connect(self._on_tab_context_menu)
        layout.addWidget(self._tab_bar)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._tabs: list[EditorTab] = []

    def add_tab(self, title: str = None, content: str = "") -> Editor:
        title = title or tr("untitled")
        tab = EditorTab()
        if content:
            tab.set_plain_text(content)
        self._tabs.append(tab)

        idx = self._stack.addWidget(tab)
        self._tab_bar.addTab(title)
        self._tab_bar.setCurrentIndex(idx)

        tab.editor.document().modificationChanged.connect(
            lambda m, t=tab: self._update_tab_display_for_tab(t)
        )

        self._on_tab_changed(idx)
        return tab.editor

    def get_current_editor(self) -> Editor:
        w = self._stack.currentWidget()
        return w.editor if w else None

    def get_current_tab(self) -> EditorTab:
        return self._stack.currentWidget()

    def count(self) -> int:
        return self._stack.count()

    def widget(self, index: int) -> EditorTab:
        return self._stack.widget(index)

    def current_index(self) -> int:
        return self._stack.currentIndex()

    def _on_tab_changed(self, index: int):
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)
            tab = self._stack.widget(index)
            if tab:
                self.editor_changed.emit(tab.editor)
                if tab.file_path:
                    self.file_changed.emit(tab.file_path)

    def _close_tab(self, index: int):
        if self._stack.count() <= 1:
            return
        tab = self._stack.widget(index)
        if tab and tab.is_modified():
            reply = QMessageBox.question(
                self, tr("unsaved_title"),
                tr("tab_unsaved_close").format(title=tab.title),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self._tab_bar.removeTab(index)
        w = self._stack.widget(index)
        self._stack.removeWidget(w)
        self._tabs.pop(index)
        if w:
            self.tab_closed.emit(w)
            w.deleteLater()

    def _update_tab_display(self, index: int):
        if index < 0 or index >= self._tab_bar.count():
            return
        tab = self._stack.widget(index)
        if not tab:
            return
        title = tab.title
        if tab.is_modified() and not title.startswith("● "):
            title = "● " + title
        elif not tab.is_modified() and title.startswith("● "):
            title = title[2:]
        self._tab_bar.setTabText(index, title)

    def _update_tab_display_for_tab(self, tab: "EditorTab"):
        for i in range(self._stack.count()):
            if self._stack.widget(i) is tab:
                self._update_tab_display(i)
                return

    def update_tab_title(self, title: str):
        idx = self._stack.currentIndex()
        if 0 <= idx < self._stack.count():
            tab = self._stack.widget(idx)
            if tab:
                tab._title = title
            self._update_tab_display(idx)

    def set_tab_file_path(self, path: str):
        idx = self._stack.currentIndex()
        if 0 <= idx < self._stack.count():
            tab = self._stack.widget(idx)
            if tab:
                tab.file_path = path
            self._update_tab_display(idx)
            self.file_changed.emit(path)

    def has_unsaved_changes(self) -> bool:
        for i in range(self._stack.count()):
            tab = self._stack.widget(i)
            if tab and tab.is_modified():
                return True
        return False

    def _on_tab_context_menu(self, pos):
        index = self._tab_bar.tabAt(pos)
        if index < 0:
            return
        tab = self._stack.widget(index)
        menu = QMenu(self)
        menu.addAction(tr("tab_close"), lambda: self._close_tab(index))
        menu.addAction(tr("tab_close_others"), lambda: self._close_others(index))
        if tab and tab.file_path:
            menu.addSeparator()
            menu.addAction(tr("tab_copy_path"), lambda: self._copy_path(tab.file_path))
        menu.exec(self._tab_bar.mapToGlobal(pos))

    def _close_others(self, keep_idx: int):
        for i in reversed(range(self._stack.count())):
            if i != keep_idx:
                self._close_tab(i)

    def _copy_path(self, path: str):
        QApplication.clipboard().setText(path)

    def apply_editor_settings(self, config: dict):
        for i in range(self._stack.count()):
            tab = self._stack.widget(i)
            if tab:
                tab.editor.update_settings(config)

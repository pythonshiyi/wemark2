import re
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem


class OutlinePanel(QWidget):
    """文档大纲导航面板，解析 Markdown 标题并支持点击跳转。"""

    heading_clicked = Signal(int)  # 行号

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(12)
        self._tree.setAnimated(True)
        self._tree.setStyleSheet(
            "QTreeWidget { border: none; background: transparent; font-size: 12px; }"
            "QTreeWidget::item { padding: 4px 6px; border-radius: 3px; }"
            "QTreeWidget::item:hover { background: #f0f4ff; color: #1a73e8; }"
            "QTreeWidget::item:selected { background: #e8f0fe; color: #1565c0; }"
        )
        self._tree.setCursor(Qt.PointingHandCursor)
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree)

    def update_outline(self, markdown: str):
        self._tree.clear()
        if not markdown:
            return
        lines = markdown.split("\n")
        stack = [(0, self._tree.invisibleRootItem())]  # (level, parent_item)

        for line_num, line in enumerate(lines, 1):
            m = re.match(r'^(#{1,6})\s+(.+?)(?:\s+#+)?$', line)
            if not m:
                continue
            level = len(m.group(1))
            title = m.group(2).strip()

            # 找到合适的父节点
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1] if stack else self._tree.invisibleRootItem()

            item = QTreeWidgetItem([title])
            item.setData(0, Qt.UserRole, line_num)
            font = item.font(0)
            if level == 1:
                font.setPointSize(font.pointSize() + 1)
                font.setBold(True)
            elif level == 2:
                font.setBold(True)
            item.setFont(0, font)
            parent.addChild(item)
            stack.append((level, item))

        self._tree.expandAll()

    def _on_item_clicked(self, item, col):
        line = item.data(0, Qt.UserRole)
        if line:
            self.heading_clicked.emit(line)

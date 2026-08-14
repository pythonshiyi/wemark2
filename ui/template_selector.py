from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox


TEMPLATE_LABELS = {
    "default": "默认主题",
    "paper": "素纸笔记",
    "coral": "珊瑚暖调",
    "nord": "北极冰蓝",
    "typewriter": "打字机",
    "literary": "文艺书香",
    "academic": "学术论文",
    "magazine": "时尚杂志",
    "news": "新闻报刊",
    "minimal": "极简白",
    "business": "商务蓝",
    "tech": "科技暗蓝",
    "fresh": "清新自然",
    "cloud": "云端漫步",
    "ocean": "海洋微风",
    "forest": "林间晨光",
    "sunset": "日落余晖",
    "warm": "温暖治愈",
    "cozy": "温馨小筑",
    "lavender": "薰衣草田",
    "retro": "复古怀旧",
    "elegant_dark": "暗黑优雅",
    "impact": "视觉冲击",
}

TEMPLATE_ORDER = list(TEMPLATE_LABELS.keys())


class TemplateSelector(QComboBox):
    template_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(120)
        self._loading = False
        self._refresh()
        self.currentIndexChanged.connect(self._on_changed)

    def _refresh(self):
        self._loading = True
        current = self.currentData()
        self.clear()
        for name in TEMPLATE_ORDER:
            label = TEMPLATE_LABELS.get(name, name)
            self.addItem(label, name)
        if current and current in TEMPLATE_ORDER:
            self.set_current_template(current)
        self._loading = False

    def current_template(self) -> str:
        return self.currentData()

    def set_current_template(self, name: str):
        for i in range(self.count()):
            if self.itemData(i) == name:
                self.setCurrentIndex(i)
                return

    def _on_changed(self, index: int):
        if not self._loading and index >= 0:
            self.template_changed.emit(self.currentData())

    def refresh(self):
        self._refresh()

"""暗色/亮色主题管理。"""

DARK_STYLE = """
/* 全局 */
QMainWindow, QDialog, QWidget { background-color: #1e1e2e; color: #cdd6f4; }
QMenuBar { background-color: #181825; color: #cdd6f4; border-bottom: 1px solid #313244; }
QMenuBar::item:selected { background-color: #45475a; }
QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #313244; }
QMenu::item:selected { background-color: #45475a; }
QToolBar { background-color: #181825; border-bottom: 1px solid #313244; }
QStatusBar { background-color: #181825; color: #a6adc8; border-top: 1px solid #313244; }
QTabBar::tab { background-color: #181825; color: #a6adc8; padding: 6px 16px; border: none; }
QTabBar::tab:selected { background-color: #1e1e2e; color: #cdd6f4; border-bottom: 2px solid #89b4fa; }
QTabBar::tab:hover { background-color: #313244; }
QScrollBar:vertical { background: #181825; width: 8px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox { 
    background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; 
    border-radius: 4px; padding: 4px 8px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #313244; color: #cdd6f4; selection-background-color: #45475a; }
QPushButton { background-color: #45475a; color: #cdd6f4; border: 1px solid #585b70; border-radius: 4px; padding: 4px 12px; }
QPushButton:hover { background-color: #585b70; }
QCheckBox { color: #cdd6f4; }
QGroupBox { color: #a6adc8; border: 1px solid #45475a; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
QDockWidget { color: #cdd6f4; }
QDockWidget::title { background-color: #181825; padding: 4px 8px; border-bottom: 1px solid #313244; }
QProgressBar { background-color: #313244; border-radius: 4px; }
QProgressBar::chunk { background-color: #89b4fa; border-radius: 4px; }
QScrollArea { border: none; }
QLabel { color: #cdd6f4; }
#Editor { background-color: #1e1e2e; color: #cdd6f4; selection-background-color: #45475a; }
"""

LIGHT_STYLE = """
/* 全局 */
QMainWindow, QDialog, QWidget { background-color: #ffffff; color: #333333; }
QMenuBar { background-color: #fafafa; color: #333333; border-bottom: 1px solid #e0e0e0; }
QMenuBar::item:selected { background-color: #e8f0fe; }
QMenu { background-color: #ffffff; color: #333333; border: 1px solid #e0e0e0; }
QMenu::item:selected { background-color: #e8f0fe; }
QToolBar { background-color: #fafafa; border-bottom: 1px solid #e0e0e0; }
QStatusBar { background-color: #fafafa; color: #666666; border-top: 1px solid #e0e0e0; }
QTabBar::tab { background-color: #f5f5f5; color: #666666; padding: 6px 16px; border: none; border-right: 1px solid #e0e0e0; }
QTabBar::tab:selected { background-color: #ffffff; color: #1a73e8; border-bottom: 2px solid #1a73e8; }
QTabBar::tab:hover { background-color: #e8e8e8; }
QScrollBar:vertical { background: #f5f5f5; width: 8px; }
QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff; color: #333333; border: 1px solid #d0d0d0;
    border-radius: 4px; padding: 4px 8px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #ffffff; color: #333333; selection-background-color: #e8f0fe; }
QPushButton { background-color: #f0f0f0; color: #333333; border: 1px solid #d0d0d0; border-radius: 4px; padding: 4px 12px; }
QPushButton:hover { background-color: #e0e0e0; }
QCheckBox { color: #333333; }
QGroupBox { color: #666666; border: 1px solid #d0d0d0; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
QDockWidget { color: #333333; }
QDockWidget::title { background-color: #fafafa; padding: 4px 8px; border-bottom: 1px solid #e0e0e0; }
QProgressBar { background-color: #f0f0f0; border-radius: 4px; }
QProgressBar::chunk { background-color: #1a73e8; border-radius: 4px; }
QScrollArea { border: none; }
QLabel { color: #333333; }
#Editor { background-color: #ffffff; color: #333333; selection-background-color: #bbdefb; }
"""

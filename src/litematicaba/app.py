from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from litematicaba.core.config import (
    set_user_accepted_unwritable_data_dir,
    user_data_dir_is_writable,
)
# 设置项
from litematicaba.core.settings import load_settings
# 主窗口
from litematicaba.ui.main_window import MainWindow
# 主题
from litematicaba.ui.theme import apply_theme

# app启动画面
try:
    import pyi_splash
    pyi_splash.close()
except ImportError:
    pass

def main() -> int:
    # 创建应用实例
    app = QApplication(sys.argv)

    # 检查目录可写性
    if getattr(sys, "frozen", False) and not user_data_dir_is_writable():
        r = QMessageBox.question(
            None,
            "数据目录不可用",
            "当前目录无法写入数据，你的修改可能会在关闭软件后全部丢失。建议更换该软件的存放位置。你确定仍要继续在这个环境下使用软件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return 0
        set_user_accepted_unwritable_data_dir()

    # 加载设置
    settings = load_settings()
    apply_theme(app, settings.theme_id)

    # 创建窗口
    window = MainWindow() # 主窗口
    window.show()

    # 事件循环
    return app.exec()

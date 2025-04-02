"""程序入口模块"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui import TranslatorApp

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 设置应用图标 - 新增代码
    icon_path = os.path.join(os.path.dirname(__file__), "translate.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    # 创建并显示主窗口
    translator = TranslatorApp()
    translator.setWindowIcon(app_icon)  # 也设置主窗口的图标
    translator.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
"""程序入口模块"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui import TranslatorApp

def resource_path(relative_path):
    """获取资源的绝对路径，兼容开发环境和PyInstaller打包环境"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    
    return os.path.join(base_path, relative_path)

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 改进的图标加载方式
    icon_path = resource_path("translate.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    # 创建并显示主窗口
    translator = TranslatorApp()
    translator.setWindowIcon(app_icon)  # 也设置主窗口的图标
    translator.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
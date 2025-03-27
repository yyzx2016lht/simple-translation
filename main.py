"""程序入口模块"""
import sys
from PySide6.QtWidgets import QApplication
from ui import TranslatorApp

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    translator = TranslatorApp()
    translator.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
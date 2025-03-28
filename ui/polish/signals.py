"""AI润色窗口的信号定义"""
from PySide6.QtCore import QObject, Signal

class PolishSignals(QObject):
    """AI润色窗口使用的信号集合"""
    update_raw_text = Signal(str)  # 用于传递原始文本，在主线程中处理
    finished = Signal()            # 完成信号
    error = Signal(str)            # 错误信号
    reset_stop_button = Signal()   # 重置停止按钮信号
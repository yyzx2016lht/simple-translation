"""翻译工作线程"""
import time
import concurrent.futures
from PySide6.QtCore import QRunnable, QObject, Signal, Slot

from config.config import MAX_BATCH_SIZE, MAX_WORKERS
from config.api import translate_single, translate_batch, get_friendly_error_message

# --- 线程通信类 ---
class WorkerSignals(QObject):
    finished = Signal(str)  # 翻译结果和耗时
    error = Signal(str)     # 错误信息
    progress = Signal(int)  # 进度百分比

# --- 翻译工作线程 ---
class TranslateWorker(QRunnable):
    """处理翻译操作的工作线程"""
    
    def __init__(self, lines, source_lang, target_lang):
        """初始化工作线程"""
        super().__init__()
        self.lines = lines
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.signals = WorkerSignals()
        self._stop_flag = False
        
    def stop(self):
        """设置停止标志"""
        self._stop_flag = True
        # 如果需要立即中断请求，可以尝试关闭会话
        try:
            from config.config import session
            # 创建新会话以中断正在进行的请求
            # 注意：这可能导致其他操作也被中断
            from config.config_manager import config_manager
            config_manager.init_session()
        except Exception as e:
            print(f"中断请求时出错: {e}")
        
    @Slot()
    def run(self):
        """执行翻译任务"""
        try:
            # 检查是否单行翻译
            if len(self.lines) == 1:
                # 检查停止标志
                if self._stop_flag:
                    return
                    
                # 单行翻译
                start_time = time.time()
                result = translate_single(self.lines[0], self.source_lang, self.target_lang)
                elapsed = round(time.time() - start_time, 2)
                self.signals.finished.emit(f"{result}|{elapsed}")
            else:
                # 批量翻译
                total_lines = len(self.lines)
                translated_results = []
                
                # 分批处理
                batch_size = MAX_BATCH_SIZE
                start_time = time.time()
                
                for i in range(0, total_lines, batch_size):
                    # 检查停止标志
                    if self._stop_flag:
                        return
                        
                    batch = self.lines[i:i+batch_size]
                    percent = min(100, int((i / total_lines) * 100))
                    self.signals.progress.emit(percent)
                    
                    try:
                        batch_result = translate_batch(batch, self.source_lang, self.target_lang)
                        translated_results.extend(batch_result)
                    except Exception as e:
                        error_msg = get_friendly_error_message(e)
                        self.signals.error.emit(f"批量翻译错误 ({i}/{total_lines}): {error_msg}")
                        return
                
                elapsed = round(time.time() - start_time, 2)
                combined_text = "\n".join(translated_results)
                self.signals.finished.emit(f"{combined_text}|{elapsed}")
                
        except Exception as e:
            error_msg = get_friendly_error_message(e)
            self.signals.error.emit(error_msg)
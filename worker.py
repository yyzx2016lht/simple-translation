"""翻译工作线程"""
import time
import concurrent.futures
from PySide6.QtCore import QRunnable, QObject, Signal, Slot

from config import MAX_BATCH_SIZE, MAX_WORKERS
from api import translate_single, translate_batch, get_friendly_error_message

# --- 线程通信类 ---
class WorkerSignals(QObject):
    finished = Signal(str)  # 翻译结果和耗时
    error = Signal(str)     # 错误信息
    progress = Signal(int)  # 进度百分比

# --- 翻译工作线程 ---
class TranslateWorker(QRunnable):
    def __init__(self, lines, source_lang, target_lang):
        super().__init__()
        self.lines = lines
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.signals = WorkerSignals()
        
    @Slot()
    def run(self):
        try:
            start_time = time.time()
            
            # 单行文本直接翻译
            if len(self.lines) == 1:
                translated_text = translate_single(
                    self.lines[0], 
                    self.source_lang, 
                    self.target_lang
                )
                elapsed = time.time() - start_time
                self.signals.finished.emit(f"{translated_text}|{elapsed:.2f}")
            
            # 多行文本使用并行处理
            else:
                # 动态调整批次大小
                batch_size = min(MAX_BATCH_SIZE, max(5, len(self.lines) // 3))
                batches = [self.lines[i:i+batch_size] for i in range(0, len(self.lines), batch_size)]
                
                # 创建并行执行器
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(batches))) as executor:
                    # 提交所有批次的翻译任务
                    future_to_batch = {
                        executor.submit(
                            translate_batch,
                            batch, 
                            self.source_lang, 
                            self.target_lang
                        ): i for i, batch in enumerate(batches)
                    }
                    
                    # 收集结果（保持顺序）
                    all_results = [None] * len(batches)
                    completed = 0
                    
                    for future in concurrent.futures.as_completed(future_to_batch):
                        batch_index = future_to_batch[future]
                        try:
                            results = future.result()
                            all_results[batch_index] = results
                            completed += 1
                            self.signals.progress.emit(int(completed * 100 / len(batches)))
                        except Exception as exc:
                            print(f"批次 {batch_index} 失败: {exc}")
                            raise exc
                
                # 展平结果
                translated_lines = [line for batch in all_results for line in batch]
                final_translation = "\n".join(translated_lines)
                elapsed = time.time() - start_time
                self.signals.finished.emit(f"{final_translation}|{elapsed:.2f}")
            
        except Exception as e:
            error_msg = get_friendly_error_message(e)
            self.signals.error.emit(error_msg)
"""AI润色窗口的文本处理和翻译逻辑"""
import threading
from PySide6.QtCore import QTimer, QObject
from PySide6.QtWidgets import QMessageBox, QApplication

from ollama_translator import OllamaTranslator
from .utils import process_thinking_tags

class TextHandler(QObject):
    """文本处理和翻译逻辑处理类"""
    
    def __init__(self, parent, signals):
        super().__init__(parent)
        self.parent = parent
        self.signals = signals
        self.translator = None
        self.translation_thread = None
        self.is_translating = False
        
        # 文本状态变量
        self.raw_text = ""
        self.processed_text = ""
        self.debug_mode = False
    
    def start_translation(self, text, model_name, source_lang, target_lang, temperature, use_stream):
        """开始翻译/润色任务"""
        if self.is_translating:
            return False
            
        if not text.strip():
            QMessageBox.warning(self.parent, "警告", "请输入要润色/翻译的文本")
            return False
            
        try:
            # 初始化翻译器（如果尚未初始化或模型已更改）
            if self.translator is None or self.translator.model != model_name:
                self.translator = OllamaTranslator(model=model_name)
            
            # 设置状态
            self.is_translating = True
            self.raw_text = ""
            self.processed_text = ""
            
            # 启动翻译线程
            self.translation_thread = threading.Thread(
                target=self._translation_thread,
                args=(text, source_lang, target_lang, temperature, use_stream),
                daemon=True
            )
            self.translation_thread.start()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self.parent, "错误", f"初始化翻译器失败: {e}")
            return False
    
    def stop_translation(self, model_name):
        """停止翻译/润色任务"""
        if not self.is_translating:
            return
            
        self.is_translating = False
        
        # 在后台线程中执行停止命令，避免UI冻结
        stop_thread = threading.Thread(
            target=self._stop_model_thread,
            args=(model_name,),
            daemon=True
        )
        stop_thread.start()
    
    def _translation_thread(self, text, source_lang, target_lang, temperature, use_stream):
        """翻译线程 - 增强版"""
        try:
            if use_stream:
                def update_ui(current_text):
                    if not self.is_translating:
                        return False
                    
                    try:
                        # 发送原始文本到主线程处理
                        self.signals.update_raw_text.emit(current_text)
                    except Exception as e:
                        print(f"更新UI时出错: {e}")
                    return True
                
                # 使用回调函数进行流式翻译
                self.translator.translate(
                    text=text,
                    source_lang=source_lang, 
                    target_lang=target_lang,
                    temperature=temperature,
                    stream=True,
                    update_callback=update_ui
                )
            else:
                # 非流式输出
                result = self.translator.translate(
                    text=text,
                    source_lang=source_lang, 
                    target_lang=target_lang,
                    temperature=temperature,
                    stream=False
                )
                
                # 发送结果
                if self.is_translating:
                    self.signals.update_raw_text.emit(result)
            
            # 完成处理
            if self.is_translating:
                self.signals.finished.emit()
                    
        except Exception as e:
            print(f"翻译线程出错: {e}")
            if self.is_translating:
                self.signals.error.emit(str(e))
    
    def _stop_model_thread(self, model_name):
        """执行停止模型的命令"""
        try:
            # 执行 ollama stop 命令
            print(f"正在停止模型: {model_name}")
            import subprocess
            subprocess.run(["ollama", "stop", model_name], check=True)
            print(f"已成功停止模型: {model_name}")
        except Exception as e:
            print(f"停止模型时发生未知错误: {e}")
        finally:
            # 发射信号通知主线程重置按钮
            self.signals.reset_stop_button.emit()
    
    def handle_incoming_text(self, text):
        """处理新收到的文本 - 返回处理后的文本和是否需要完全替换"""
        # 存储原始文本
        self.raw_text = text
        
        # 处理思考标签
        new_processed_text = process_thinking_tags(text, self.debug_mode)
        
        # 判断是追加还是替换
        need_full_replace = False
        
        # 如果当前没有处理过的文本，或新文本不是当前文本的延续
        if not self.processed_text or not new_processed_text.startswith(self.processed_text):
            need_full_replace = True
        
        # 更新处理后的文本
        self.processed_text = new_processed_text
        
        return new_processed_text, need_full_replace
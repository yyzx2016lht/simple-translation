"""AI润色窗口"""
import sys
import json
import time
import os
from pathlib import Path
import threading
import subprocess

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QTextCursor, QTextOption
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QFormLayout, QMessageBox, QProgressBar,
    QGroupBox, QSplitter, QApplication, QPlainTextEdit
)

from ollama_translator import OllamaTranslator

# 修改LANGUAGE_MAPPING，添加自动检测选项
LANGUAGE_MAPPING = {
    "Auto": "自动检测", 
    "Chinese": "中文", 
    "English": "英文", 
    "Japanese": "日文", 
    "Korean": "韩文", 
    "French": "法文", 
    "German": "德文", 
    "Russian": "俄文", 
    "Spanish": "西班牙文"
}

# 修改PolishSignals类，添加原始文本信号
class PolishSignals(QObject):
    update_raw_text = Signal(str)  # 用于传递原始文本，在主线程中处理
    finished = Signal()        # 完成信号
    error = Signal(str)        # 错误信号
    reset_stop_button = Signal()  # 重置停止按钮信号

class AIPolishWindow(QDialog):
    def __init__(self, parent=None, initial_text=""):
        super().__init__(parent)
        self.parent = parent
        self.initial_text = initial_text
        self.translator = None
        self.translation_thread = None
        self.is_translating = False
        self.signals = PolishSignals()
        
        # 存储原始和处理后的文本
        self.raw_text = ""  # 原始文本(包含思考标签)
        self.processed_text = ""  # 处理后的文本(移除思考标签)
        self.last_length = 0  # 上次更新长度
        
        self.initUI()
        self.loadModels()
        
        # 连接信号 - 确保在主线程中处理UI
        self.signals.update_raw_text.connect(self.handleIncomingText)
        self.signals.finished.connect(self.onTranslationFinished)
        self.signals.error.connect(self.onTranslationError)
        self.signals.reset_stop_button.connect(self.resetStopButton)
        
        # 初始化输入文本
        if initial_text:
            self.input_text.setPlainText(initial_text)
    
    def handleIncomingText(self, text):
        """处理从翻译线程收到的文本 - 在主线程中执行"""
        if not self.is_translating:
            return
            
        # 存储原始文本
        self.raw_text = text
        
        # 处理思考标签
        new_processed_text = self.process_thinking_tags(text)
        
        # 判断是追加还是替换
        if new_processed_text.startswith(self.processed_text) and len(new_processed_text) > len(self.processed_text):
            # 可以增量更新，获取新增部分
            delta = new_processed_text[len(self.processed_text):]
            
            # 保存当前滚动位置
            scrollbar = self.output_text.verticalScrollBar()
            at_bottom = scrollbar.value() >= scrollbar.maximum() - 30
            
            # 将光标移到末尾并插入新文本
            cursor = self.output_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.output_text.setTextCursor(cursor)
            self.output_text.insertPlainText(delta)
            
            # 如果之前在底部，保持在底部
            if at_bottom:
                scrollbar.setValue(scrollbar.maximum())
        else:
            # 需要完全替换文本
            current_scroll = self.output_text.verticalScrollBar().value()
            self.output_text.setPlainText(new_processed_text)
            
            # 尝试保持滚动位置
            new_max = self.output_text.verticalScrollBar().maximum()
            if current_scroll < new_max:
                self.output_text.verticalScrollBar().setValue(current_scroll)
        
        # 更新已处理文本记录
        self.processed_text = new_processed_text
    
    def process_thinking_tags(self, text):
        """处理大模型输出中的<think></think>标签"""
        import re
        
        # 先处理完整的思考标签
        pattern = r'<think>.*?</think>'
        processed = re.sub(pattern, '', text, flags=re.DOTALL)
        
        # 处理未闭合的思考标签
        open_tag_pos = processed.find('<think>')
        if (open_tag_pos >= 0):
            processed = processed[:open_tag_pos] + ' [🤔思考中...] '
        
        return processed

    # 修改initUI方法中的语言选择部分
    def initUI(self):
        self.setWindowTitle("AI润色/翻译")
        self.setMinimumSize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 顶部控制区域
        control_group = QGroupBox("模型与参数设置")
        control_layout = QVBoxLayout(control_group)
        
        # 第一行：模型选择和添加
        model_layout = QHBoxLayout()
        
        # 模型选择
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        
        # 添加新模型
        self.new_model_input = QLineEdit()
        self.new_model_input.setPlaceholderText("输入新模型名称...")
        
        add_model_btn = QPushButton("添加模型")
        add_model_btn.clicked.connect(self.addNewModel)
        
        model_layout.addWidget(QLabel("选择模型:"))
        model_layout.addWidget(self.model_combo, 1)
        model_layout.addWidget(self.new_model_input, 1)
        model_layout.addWidget(add_model_btn)
        
        control_layout.addLayout(model_layout)
        
        # 第二行：参数设置
        params_layout = QFormLayout()
        
        # 源语言选择框
        self.source_lang_combo = QComboBox()
        for code, name in LANGUAGE_MAPPING.items():
            self.source_lang_combo.addItem(f"{name}（{code}）", code)

        # 设置默认源语言为自动检测
        for i in range(self.source_lang_combo.count()):
            if self.source_lang_combo.itemData(i) == "Auto":
                self.source_lang_combo.setCurrentIndex(i)
                break
        
        # 目标语言选择框
        self.target_lang_combo = QComboBox()
        for code, name in LANGUAGE_MAPPING.items():
            if code != "Auto":  # 目标语言不包含自动检测
                self.target_lang_combo.addItem(f"{name}（{code}）", code)

        # 设置默认目标语言为中文
        for i in range(self.target_lang_combo.count()):
            if self.target_lang_combo.itemData(i) == "Chinese":
                self.target_lang_combo.setCurrentIndex(i)
                break
        
        # 添加自定义选项
        self.target_lang_combo.addItem("自定义语言...", "custom")
        
        # 自定义语言输入框（初始隐藏）
        self.custom_lang_input = QLineEdit()
        self.custom_lang_input.setPlaceholderText("输入目标语言名称（如：德语、French等）")
        self.custom_lang_input.setVisible(False)
        
        # 连接信号：当目标语言改变时调用处理函数
        self.target_lang_combo.currentIndexChanged.connect(self.onTargetLangChanged)
        
        # 温度参数
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.1, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        
        # 是否流式输出
        self.stream_checkbox = QCheckBox("启用")
        self.stream_checkbox.setChecked(True)
        
        # 在添加目标语言控件时，添加自定义语言输入框
        params_layout.addRow("源语言:", self.source_lang_combo)
        params_layout.addRow("目标语言:", self.target_lang_combo)
        params_layout.addRow("", self.custom_lang_input)  # 空标签使其与目标语言对齐
        params_layout.addRow("温度:", self.temperature_spin)
        params_layout.addRow("流式输出:", self.stream_checkbox)
        
        control_layout.addLayout(params_layout)
        
        # 添加到主布局
        main_layout.addWidget(control_group)
        
        # 输入区域
        input_group = QGroupBox("输入文本")
        input_layout = QVBoxLayout(input_group)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("在此输入要润色/翻译的文本...")
        input_layout.addWidget(self.input_text)
        
        # 在btn_layout添加按钮的代码部分
        btn_layout = QHBoxLayout()

        self.translate_btn = QPushButton("开始润色/翻译")
        self.translate_btn.clicked.connect(self.startTranslation)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stopTranslation)
        self.stop_btn.setEnabled(False)

        # 添加粘贴按钮
        paste_btn = QPushButton("粘贴")
        paste_btn.clicked.connect(self.pasteText)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clearInput)

        btn_layout.addWidget(self.translate_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(paste_btn)  # 新增粘贴按钮
        btn_layout.addWidget(clear_btn)
        
        input_layout.addLayout(btn_layout)
        
        splitter.addWidget(input_group)
        
        # 输出区域
        output_group = QGroupBox("结果")
        output_layout = QVBoxLayout(output_group)
        
        # 在 initUI 方法中修改输出框部分
        # 使用 QPlainTextEdit 替代 QTextEdit，性能更好
        self.output_text = QPlainTextEdit()
        self.output_text.setPlaceholderText("润色/翻译结果将显示在这里...")
        self.output_text.setReadOnly(True)
        # 添加这些关键设置
        self.output_text.setLineWrapMode(QPlainTextEdit.WidgetWidth)  # 自动换行
        self.output_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # 总是显示垂直滚动条
        self.output_text.setMaximumBlockCount(0)  # 不限制文本块数量
        self.output_text.setUndoRedoEnabled(False)  # 禁用撤销/重做以提高性能
        # 在初始化过程中添加性能优化设置
        self.output_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)  # 更高效的换行模式
        self.output_text.document().setDocumentMargin(8)  # 减小边距提高渲染效率
        self.output_text.setCenterOnScroll(False)  # 禁用滚动居中以提高性能
        output_layout.addWidget(self.output_text)
        
        # 结果操作按钮
        result_btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("复制结果")
        copy_btn.clicked.connect(self.copyResult)
        
        apply_btn = QPushButton("应用到主窗口")
        apply_btn.clicked.connect(self.applyToMainWindow)
        
        result_btn_layout.addWidget(copy_btn)
        result_btn_layout.addWidget(apply_btn)
        
        output_layout.addLayout(result_btn_layout)
        
        splitter.addWidget(output_group)
        
        # 设置初始比例
        splitter.setSizes([300, 300])
        
        main_layout.addWidget(splitter)
    
    def loadModels(self):
        """加载已保存的模型列表和当前已安装的模型"""
        models_file = Path(os.path.expanduser("~")) / ".translator_models.json"
        
        # 获取已安装的模型
        installed_models = get_installed_ollama_models()
        
        # 如果没有检测到模型，提示用户
        if not installed_models:
            QMessageBox.warning(self, "提示", "本地还没有通过 Ollama 部署的大模型，快去安装一个吧！")
            default_models = []
        else:
            # 使用第一个检测到的模型作为默认模型
            default_models = [installed_models[0]]
        
        # 从文件加载保存的模型
        saved_models = []
        if models_file.exists():
            try:
                with open(models_file, 'r', encoding='utf-8') as f:
                    saved_models = json.load(f)
            except Exception as e:
                print(f"读取模型列表出错: {e}")
        
        # 合并所有模型列表
        all_models = list(set(default_models + saved_models + installed_models))
        
        # 填充下拉框
        self.model_combo.clear()
        for model in all_models:
            self.model_combo.addItem(model)
    
    def saveModels(self):
        """保存模型列表"""
        models = [self.model_combo.itemText(i) for i in range(self.model_combo.count())]
        models_file = Path(os.path.expanduser("~")) / ".translator_models.json"
        
        try:
            with open(models_file, 'w', encoding='utf-8') as f:
                json.dump(models, f)
        except Exception as e:
            print(f"保存模型列表出错: {e}")
    
    def addNewModel(self):
        """添加新模型到列表"""
        model_name = self.new_model_input.text().strip()
        if not model_name:
            QMessageBox.warning(self, "警告", "请输入模型名称")
            return
        
        # 检查是否已存在
        for i in range(self.model_combo.count()):
            if self.model_combo.itemText(i) == model_name:
                QMessageBox.information(self, "提示", "该模型已在列表中")
                return
        
        # 添加并选中
        self.model_combo.addItem(model_name)
        self.model_combo.setCurrentText(model_name)
        
        # 清空输入框
        self.new_model_input.clear()
        
        # 保存模型列表
        self.saveModels()
    
    # 修改startTranslation方法中获取语言的部分
    def startTranslation(self):
        """开始翻译/润色"""
        if self.is_translating:
            return
        
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要润色/翻译的文本")
            return
        
        model_name = self.model_combo.currentText()
        
        # 源语言：使用映射或保持自动检测
        source_lang_code = self.source_lang_combo.currentData()
        source_lang = LANGUAGE_MAPPING.get(source_lang_code, "Auto")

        # 目标语言：检查是否使用自定义输入
        target_lang_code = self.target_lang_combo.currentData()
        if target_lang_code == "custom":
            custom_lang = self.custom_lang_input.text().strip()
            if not custom_lang:
                QMessageBox.warning(self, "警告", "请输入自定义目标语言")
                return
            target_lang = custom_lang
        else:
            target_lang = LANGUAGE_MAPPING.get(target_lang_code, "Chinese")
        
        temperature = self.temperature_spin.value()
        use_stream = self.stream_checkbox.isChecked()
        
        try:
            # 初始化翻译器（如果尚未初始化或模型已更改）
            if self.translator is None or self.translator.model != model_name:
                self.translator = OllamaTranslator(model=model_name)
            
            # 准备UI
            self.translate_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.output_text.clear()
            self.is_translating = True
            
            # 启动翻译线程
            self.translation_thread = threading.Thread(
                target=self._translation_thread,
                args=(text, source_lang, target_lang, temperature, use_stream),
                daemon=True
            )
            self.translation_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"初始化翻译器失败: {e}")
            self.is_translating = False
            self.translate_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def _translation_thread(self, text, source_lang, target_lang, temperature, use_stream):
        """翻译线程"""
        try:
            # 重置文本状态
            self.raw_text = ""
            self.processed_text = ""
            self.output_text.clear()  # 清空输出框
            
            if use_stream:
                # 定义流式更新回调
                def update_ui(current_text):
                    if not self.is_translating:
                        return False  # 返回False提示模型停止生成
                    
                    # 发送原始文本到主线程处理
                    self.signals.update_raw_text.emit(current_text)
                    return True
                
                # 使用回调函数进行翻译
                self.translator.translate(
                    text=text,
                    source_lang=source_lang, 
                    target_lang=target_lang,
                    temperature=temperature,
                    stream=True,
                    update_callback=update_ui
                )
            else:
                # 非流式输出 - 一次性获取结果
                result = self.translator.translate(
                    text=text,
                    source_lang=source_lang, 
                    target_lang=target_lang,
                    temperature=temperature,
                    stream=False
                )
                
                # 发送结果到主线程处理
                if self.is_translating:
                    self.signals.update_raw_text.emit(result)
            
            # 完成处理
            if self.is_translating:
                self.signals.finished.emit()
                    
        except Exception as e:
            if self.is_translating:
                self.signals.error.emit(str(e))
    
    # 修改updateOutputText方法
    def updateOutputText(self, text):
        """智能更新输出文本（带虚拟滚动支持）"""
        # 处理思考标签
        processed_text = self.process_thinking_tags(text)
        
        # 更新结果变量
        self.result_text = text
        
        # 虚拟滚动：如果文本过长，只显示最后10000个字符
        MAX_VISIBLE_CHARS = 10000
        if len(processed_text) > MAX_VISIBLE_CHARS * 1.5:  # 添加缓冲空间
            display_text = "...(部分内容已省略)...\n" + processed_text[-MAX_VISIBLE_CHARS:]
        else:
            display_text = processed_text
        
        # 智能更新文本
        current_text = self.output_text.toPlainText()
        if display_text.startswith(current_text) and len(display_text) > len(current_text):
            # 只追加新内容
            new_text = display_text[len(current_text):]
            cursor = self.output_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.output_text.setTextCursor(cursor)
            self.output_text.insertPlainText(new_text)
        else:
            # 完全替换
            self.output_text.setPlainText(display_text)
        
        # 确保滚动到底部
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output_text.setTextCursor(cursor)
    
    def onTranslationFinished(self):
        """翻译/润色完成"""
        self.is_translating = False
        self.translate_btn.setEnabled(True)
        self.resetStopButton()  # 重置停止按钮

    def onTranslationError(self, error_msg):
        """翻译/润色出错"""
        self.is_translating = False
        self.translate_btn.setEnabled(True)
        self.resetStopButton()  # 重置停止按钮
        
        QMessageBox.critical(self, "翻译错误", error_msg)
    
    # 修改stopTranslation方法
    def stopTranslation(self):
        """停止翻译/润色"""
        if self.is_translating:
            self.is_translating = False
            
            # 禁用停止按钮，防止多次点击
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("正在停止...")
            
            # 获取当前模型名称
            current_model = self.model_combo.currentText()
            
            # 在后台线程中执行停止命令，避免UI冻结
            stop_thread = threading.Thread(
                target=self._stop_model_thread,
                args=(current_model,),
                daemon=True
            )
            stop_thread.start()

    def _stop_model_thread(self, model_name):
        """执行停止模型的命令"""
        try:
            # 执行 ollama stop 命令
            print(f"正在停止模型: {model_name}")
            subprocess.run(["ollama", "stop", model_name], check=True)
            print(f"已成功停止模型: {model_name}")
        except subprocess.CalledProcessError as e:
            print(f"停止模型时出错: {e}")
            QMessageBox.warning(self, "停止失败", f"无法停止模型 {model_name}。\n错误: {e}")
        except Exception as e:
            print(f"停止模型时发生未知错误: {e}")
            QMessageBox.critical(self, "停止失败", f"发生未知错误: {e}")
        finally:
            # 发射信号通知主线程重置按钮
            self.signals.reset_stop_button.emit()

    # 添加新方法
    def resetStopButton(self):
        """重置停止按钮状态"""
        self.stop_btn.setText("停止")
        self.stop_btn.setEnabled(True if self.is_translating else False)
        self.translate_btn.setEnabled(True if not self.is_translating else False)
    
    def clearInput(self):
        """清空输入和输出"""
        self.input_text.clear()
        self.output_text.clear()
        self.raw_text = ""
        self.processed_text = ""

    def resetStopButton(self):
        """重置停止按钮状态"""
        self.stop_btn.setText("停止")
        self.stop_btn.setEnabled(self.is_translating)
        self.translate_btn.setEnabled(not self.is_translating)

    def applyToMainWindow(self):
        """将结果应用到主窗口"""
        text_to_apply = ""
        if hasattr(self, 'processed_text') and self.processed_text:
            text_to_apply = self.processed_text
        else:
            text_to_apply = self.output_text.toPlainText()
            
        if text_to_apply and self.parent:
            try:
                # 假设父窗口有output_text属性
                self.parent.output_text.setText(text_to_apply)
                QMessageBox.information(self, "提示", "已应用到主窗口")
                self.accept()  # 关闭对话框
            except AttributeError:
                QMessageBox.warning(self, "错误", "无法应用到主窗口")
    
    def closeEvent(self, event):
        """关闭窗口时处理"""
        if self.is_translating:
            # 确保翻译线程停止
            self.is_translating = False
            # 获取当前模型
            current_model = self.model_combo.currentText()
            # 尝试停止模型
            try:
                import subprocess
                subprocess.run(["ollama", "stop", current_model], 
                            check=False, 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)
            except:
                pass
        
        # 继续关闭事件
        event.accept()

    # 添加处理目标语言变化的函数
    def onTargetLangChanged(self, index):
        """处理目标语言选择变化"""
        selected_data = self.target_lang_combo.currentData()
        if selected_data == "custom":
            self.custom_lang_input.setVisible(True)
        else:
            self.custom_lang_input.setVisible(False)

    # 添加粘贴功能
    def pasteText(self):
        """从剪贴板粘贴文本到输入框"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            cursor = self.input_text.textCursor()
            cursor.insertText(text)
        else:
            QMessageBox.information(self, "提示", "剪贴板中没有文本")

    def flushUpdateBuffer(self):
        """刷新更新缓冲区，将缓冲内容显示到UI"""
        if self.result_text:
            self.signals.update_text.emit(self.result_text)

    def resizeEvent(self, event):
        """窗口调整大小时保持滚动位置"""
        super().resizeEvent(event)
        
        # 处理输出框滚动位置
        if hasattr(self, 'output_text'):
            scrollbar = self.output_text.verticalScrollBar()
            # 如果在底部附近，则保持在底部
            if scrollbar.value() >= scrollbar.maximum() - 30:
                QTimer.singleShot(0, lambda: scrollbar.setValue(scrollbar.maximum()))

    def processAndUpdateText(self, raw_text):
        """在主线程中处理和更新文本 - 非常关键的新方法"""
        if not self.is_translating:
            return
            
        # 存储原始文本
        self.result_text = raw_text
        
        # 处理思考标签
        processed_text = self.process_thinking_tags(raw_text)
        
        # 计算是否为增量更新
        if processed_text.startswith(self.current_output) and len(processed_text) > len(self.current_output):
            # 获取新增文本
            new_text = processed_text[len(self.current_output):]
            
            # 追加新文本而不是替换
            cursor = self.output_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.output_text.setTextCursor(cursor)
            self.output_text.insertPlainText(new_text)
        else:
            # 文本结构发生变化，需要完全替换
            self.output_text.setPlainText(processed_text)
        
        # 更新当前输出
        self.current_output = processed_text
        
        # 确保滚动到底部
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def copyResult(self):
        """复制结果到剪贴板"""
        if hasattr(self, 'processed_text') and self.processed_text:
            QApplication.clipboard().setText(self.processed_text)
            QMessageBox.information(self, "提示", "已复制到剪贴板")
        elif self.output_text.toPlainText():
            # 如果processed_text不存在，直接使用输出框的文本
            QApplication.clipboard().setText(self.output_text.toPlainText())
            QMessageBox.information(self, "提示", "已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "没有可复制的内容")

def get_installed_ollama_models():
    """获取当前电脑已安装的Ollama模型列表"""
    try:
        # 执行ollama list命令
        result = subprocess.run(["ollama", "list"], 
                               capture_output=True, 
                               text=True, 
                               check=True)
        
        # 解析输出结果
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:  # 只有标题行，没有模型
            return []
            
        # 需要排除的非大模型列表
        exclude_models = [
            'nomic-embed-text:latest', 
            'nomic-embed-text',
            # 可以添加其他需要排除的模型
        ]
            
        # 提取模型名称（第一列）
        models = []
        for line in lines[1:]:  # 跳过标题行
            parts = line.split()
            if parts:  # 确保行不为空
                model_name = parts[0]  # 第一列是模型名称
                # 检查是否为需要排除的模型
                if model_name not in exclude_models and not any(model_name.startswith(prefix) for prefix in ["nomic-embed"]):
                    models.append(model_name)
                
        return models
    except subprocess.CalledProcessError:
        print("执行ollama list命令失败")
        return []
    except Exception as e:
        print(f"获取Ollama模型列表出错: {e}")
        return []
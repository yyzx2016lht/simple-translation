"""AI窗口组件"""
import sys
import threading
import re  # 添加用于文本处理
from PySide6.QtCore import Qt, QTimer, QObject, QMetaObject, Signal
from PySide6.QtGui import QFont, QTextCursor, QTextOption
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,  # 改为QPlainTextEdit
    QPushButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QFormLayout, QMessageBox, QGroupBox, QSplitter, 
    QApplication, QSizePolicy, QMainWindow
)

from translator.ollama_translator import OllamaTranslator
from .signals import PolishSignals
from .handlers import TextHandler
from .utils import (
    LANGUAGE_MAPPING, get_installed_ollama_models, 
    load_saved_models, save_models, process_thinking_tags
)

class EnterKeyPlainTextEdit(QPlainTextEdit):  # 改为继承QPlainTextEdit
    """自定义纯文本编辑框，支持Enter键触发翻译，Shift+Enter插入换行"""
    translateRequested = Signal()
    
    def keyPressEvent(self, event):
        # 如果按下的是Enter键
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 检查是否同时按下了Shift键
            if event.modifiers() & Qt.ShiftModifier:
                # Shift+Enter：插入换行
                super().keyPressEvent(event)
            else:
                # 仅Enter：触发翻译
                self.translateRequested.emit()
        else:
            # 其他按键正常处理
            super().keyPressEvent(event)

class AIPolishWidget(QWidget):
    """AI翻译组件"""
    def __init__(self, parent=None, initial_text=""):
        super().__init__(parent)
        self.parent = parent
        self.initial_text = initial_text
        
        # 创建信号对象
        self.signals = PolishSignals()
        
        # 创建文本处理器
        self.text_handler = TextHandler(self, self.signals)
        
        # 初始化UI
        self.initUI()
        self._loadModels()
        
        # 连接信号
        self.connectSignals()
        
        # 初始化输入文本
        if initial_text:
            self.input_text.setPlainText(initial_text)
            
        # 设置尺寸策略，允许组件在两个方向上扩展
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    def initUI(self):
        """初始化用户界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # 顶部控制区域
        control_group = QGroupBox("模型与参数设置")
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(10, 15, 10, 10)
        
        # 模型选择行 - 修改后的版本
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模       型:"))
        
        self.model_combo = QComboBox()
        model_layout.addWidget(self.model_combo, 1)
        
        # 添加提示标签
        model_tip_label = QLabel("提示：翻译尽可能不要选择思考类模型    温度值越高创意性越大，也越容易出错")
        model_tip_label.setStyleSheet("color: #666;")
        model_layout.addWidget(model_tip_label, 2)
        
        control_layout.addLayout(model_layout)
        
        # 语言与参数行
        params_layout = QHBoxLayout()
        
        # 左侧 - 语言设置
        lang_layout = QFormLayout()
        
        # 源语言
        self.source_lang_combo = QComboBox()
        for code, name in LANGUAGE_MAPPING.items():
            self.source_lang_combo.addItem(f"{name}（{code}）", code)
        
        # 设置默认源语言
        for i in range(self.source_lang_combo.count()):
            if self.source_lang_combo.itemData(i) == "Auto":
                self.source_lang_combo.setCurrentIndex(i)
                break
        
        # 目标语言
        self.target_lang_combo = QComboBox()
        for code, name in LANGUAGE_MAPPING.items():
            if code != "Auto":
                self.target_lang_combo.addItem(f"{name}（{code}）", code)
        
        # 添加自定义选项
        self.target_lang_combo.addItem("自定义语言...", "custom")
        
        lang_layout.addRow("源  语  言:", self.source_lang_combo)
        lang_layout.addRow("目标语言:", self.target_lang_combo)
        
        # 自定义语言输入框
        self.custom_lang_input = QLineEdit()
        self.custom_lang_input.setPlaceholderText("自定义语言名称")
        self.custom_lang_input.setVisible(False)
        lang_layout.addRow("", self.custom_lang_input)
        
        # 右侧 - 其他参数
        other_layout = QFormLayout()
        
        # 温度参数
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.1, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.3)
        
        # 流式输出
        self.stream_checkbox = QCheckBox("启用")
        self.stream_checkbox.setChecked(True)
        
        other_layout.addRow("温度:", self.temperature_spin)
        other_layout.addRow("流式输出:", self.stream_checkbox)
        
        # 平均分配左右两列
        params_layout.addLayout(lang_layout, 1)
        params_layout.addLayout(other_layout, 1)
        
        control_layout.addLayout(params_layout)

        # 添加快捷键提示
        shortcut_label = QLabel("提示：按Enter开始翻译，按Shift+Enter换行")
        shortcut_label.setStyleSheet("color: #666;")
        control_layout.addWidget(shortcut_label)
        
        # 添加到主布局
        main_layout.addWidget(control_group)
        
        # 输入区域
        input_group = QGroupBox("输入文本")
        input_layout = QVBoxLayout(input_group)
        
        # 创建自定义输入框处理Enter和Shift+Enter，使用QPlainTextEdit
        self.input_text = EnterKeyPlainTextEdit(self)  # 改为EnterKeyPlainTextEdit
        self.input_text.setPlaceholderText("在此输入要翻译的文本...")
        self.input_text.translateRequested.connect(self.startTranslation)
        input_layout.addWidget(self.input_text)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.translate_btn = QPushButton("开始翻译")
        self.translate_btn.clicked.connect(self.startTranslation)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stopTranslation)
        self.stop_btn.setEnabled(False)
        
        paste_btn = QPushButton("粘贴")
        paste_btn.clicked.connect(self.pasteText)
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clearInput)
        
        btn_layout.addWidget(self.translate_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(paste_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        
        input_layout.addLayout(btn_layout)
        
        splitter.addWidget(input_group)
        
        # 输出区域 - 已经是QPlainTextEdit，不需要修改
        output_group = QGroupBox("结果")
        output_layout = QVBoxLayout(output_group)
        
        self.output_text = QPlainTextEdit()
        self.output_text.setPlaceholderText("翻译结果将显示在这里...")
        self.output_text.setReadOnly(True)
        self.output_text.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        output_layout.addWidget(self.output_text)
        
        # 结果操作按钮 - 修改后的版本
        result_btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("复制结果")
        copy_btn.clicked.connect(self.copyResult)
        
        back_btn = QPushButton("返回翻译")
        back_btn.clicked.connect(self.backToTranslate)
        
        result_btn_layout.addWidget(copy_btn)
        result_btn_layout.addWidget(back_btn)
        result_btn_layout.addStretch()
        
        output_layout.addLayout(result_btn_layout)
        
        splitter.addWidget(output_group)
        
        # 输入输出框高度相等
        splitter.setSizes([300, 300])
        
        main_layout.addWidget(splitter, 1)
        
        # 连接信号
        self.target_lang_combo.currentIndexChanged.connect(self.onTargetLangChanged)
    
    def connectSignals(self):
        """连接信号和槽"""
        self.signals.update_raw_text.connect(self.processAndUpdateText)
        self.signals.finished.connect(self.onTranslationFinished)
        self.signals.error.connect(self.onTranslationError)
        self.signals.reset_stop_button.connect(self.resetStopButton)
    
    def _loadModels(self):
        """加载已安装的模型列表"""
        try:
            installed_models = get_installed_ollama_models()
            
            if not installed_models:
                # 使用对话框而不是立即退出
                reply = QMessageBox.warning(
                    self, 
                    "模型加载错误", 
                    "未能获取Ollama模型列表。<br><br>"
                    "可能原因:<br>"
                    "1. Ollama未安装或未运行<br>"
                    "请前往官网下载软件：<a href='https://ollama.com/'>https://ollama.com/</a><br>"
                    "2. 没有部署任何模型<br>"
                    "请前往官网下载模型：<a href='https://ollama.com/search'>https://ollama.com/search</a><br><br>"
                    "是否继续使用AI翻译页面？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                # 检查用户选择
                if reply == QMessageBox.No:
                    # 用户选择不继续，返回主翻译页面
                    return
                
                # 用户选择继续，添加一个占位模型
                self.model_combo.clear()
                self.model_combo.addItem("请安装Ollama模型")
                self.translate_btn.setEnabled(False)
                return
            
            # 正常情况：填充下拉框
            self.model_combo.clear()
            for model in installed_models:
                self.model_combo.addItem(model)
            self.translate_btn.setEnabled(True)
        
        except Exception as e:
            # 捕获所有异常，确保界面不会崩溃
            QMessageBox.critical(
                self, 
                "错误", 
                f"加载模型时发生错误: {str(e)}\n\n请返回主翻译界面。"
            )
            if self.parent and hasattr(self.parent, 'showTranslatePage'):
                self.parent.showTranslatePage()
    
    def onTargetLangChanged(self, index):
        """处理目标语言选择变化"""
        selected_data = self.target_lang_combo.currentData()
        self.custom_lang_input.setVisible(selected_data == "custom")
    

    def startTranslation(self):
        """开始翻译"""
        if self.text_handler.is_translating:
            return
        
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要翻译的文本")
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
        
        # 准备UI
        self.translate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.output_text.clear()
        
        # 开始翻译
        if self.text_handler.start_translation(
            text, model_name, source_lang, target_lang, temperature, use_stream
        ):
            self.text_handler.is_translating = True
        else:
            self.translate_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def stopTranslation(self):
        """停止翻译"""
        if not self.text_handler.is_translating:
            return
            
        # 获取当前模型名称
        current_model = self.model_combo.currentText()
        
        # 禁用停止按钮，防止多次点击
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("正在停止...")
        
        # 停止翻译
        self.text_handler.stop_translation(current_model)
    
    def processAndUpdateText(self, text):
        """处理和更新接收到的文本"""
        if not self.text_handler.is_translating:
            return
            
        # 处理文本
        processed_text, need_full_replace = self.text_handler.handle_incoming_text(text)
        
        # 额外过滤XML标签
        processed_text = self._filter_xml_tags(processed_text)
        
        # 处理多余的回车
        processed_text = self._normalize_newlines(processed_text)
        
        # 更新UI
        if need_full_replace or not self.output_text.toPlainText():
            # 完全替换
            self.output_text.setPlainText(processed_text)
        else:
            # 智能追加
            cursor = self.output_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.output_text.setTextCursor(cursor)
            
            # 获取当前已有文本
            current_text = self.output_text.toPlainText()
            
            # 追加新的部分
            if processed_text.startswith(current_text) and len(processed_text) > len(current_text):
                new_text = processed_text[len(current_text):]
                self.output_text.insertPlainText(new_text)
            else:
                self.output_text.setPlainText(processed_text)
        
        # 滚动到底部
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _filter_xml_tags(self, text):
        """过滤掉XML标签"""
        # 移除<text>和</text>标签
        text = re.sub(r'<text>|</text>', '', text)
        # 移除可能的其他XML标签
        text = re.sub(r'<[^>]+>', '', text)
        return text
    

    def _normalize_newlines(self, text):
        """规范化换行符，保留原始格式，但处理思考标签后的换行"""
        # 处理思考标签相关的换行问题
        text = process_thinking_tags(text)
        
        # 将连续的3个以上换行符替换为2个换行符(保留段落间距)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text

    
    def onTranslationFinished(self):
        """翻译完成"""
        self.text_handler.is_translating = False
        self.translate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("停止")
    
    def onTranslationError(self, error_msg):
        """翻译出错"""
        self.text_handler.is_translating = False
        self.translate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("停止")
        
        QMessageBox.critical(self, "翻译错误", error_msg)
    
    def resetStopButton(self):
        """重置停止按钮状态"""
        self.stop_btn.setText("停止")
        self.stop_btn.setEnabled(self.text_handler.is_translating)
        self.translate_btn.setEnabled(not self.text_handler.is_translating)
    
    def clearInput(self):
        """清空输入文本"""
        self.input_text.clear()
        self.output_text.clear()
    
    def pasteText(self):
        """从剪贴板粘贴文本到输入框"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            # 获取当前光标位置
            cursor = self.input_text.textCursor()
            # 在光标位置插入文本
            cursor.insertText(text)
        else:
            QMessageBox.information(self, "提示", "剪贴板中没有文本")
    
    def copyResult(self):
        """复制结果到剪贴板"""
        text = self.output_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "提示", "已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "没有可复制的内容")
    
    def backToTranslate(self):
        """返回翻译页面"""
        if self.parent and hasattr(self.parent, 'showTranslatePage'):
            self.parent.showTranslatePage()
"""AI润色窗口主类"""
import sys
import threading
from PySide6.QtCore import Qt, QTimer, QObject, QMetaObject
from PySide6.QtGui import QFont, QTextCursor, QTextOption
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QFormLayout, QMessageBox, QGroupBox, QSplitter, 
    QApplication, QPlainTextEdit
)

from ollama_translator import OllamaTranslator
from .signals import PolishSignals
from .handlers import TextHandler
from .utils import (
    LANGUAGE_MAPPING, get_installed_ollama_models, 
    load_saved_models, save_models, process_thinking_tags
)

class AIPolishWindow(QDialog):
    """AI润色/翻译窗口"""
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
        self.loadModels()
        
        # 连接信号
        self.connectSignals()
        
        # 初始化输入文本
        if initial_text:
            self.input_text.setPlainText(initial_text)
    
    def initUI(self):
        """初始化用户界面"""
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
        
        # 语言选择
        self.source_lang_combo = QComboBox()
        for code, name in LANGUAGE_MAPPING.items():
            self.source_lang_combo.addItem(f"{name}（{code}）", code)
        
        # 设置默认源语言为自动检测
        for i in range(self.source_lang_combo.count()):
            if self.source_lang_combo.itemData(i) == "Auto":
                self.source_lang_combo.setCurrentIndex(i)
                break
        
        # 目标语言下拉框
        self.target_lang_combo = QComboBox()
        for code, name in LANGUAGE_MAPPING.items():
            if code != "Auto":  # 目标语言不包含自动检测
                self.target_lang_combo.addItem(f"{name}（{code}）", code)
        
        # 添加自定义选项
        self.target_lang_combo.addItem("自定义语言...", "custom")
        
        # 自定义语言输入框（初始隐藏）
        self.custom_lang_input = QLineEdit()
        self.custom_lang_input.setPlaceholderText("输入目标语言名称（如：德语、French等）")
        self.custom_lang_input.setVisible(False)
        
        # 温度参数
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.1, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        
        # 是否流式输出
        self.stream_checkbox = QCheckBox("启用")
        self.stream_checkbox.setChecked(True)
        
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
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.translate_btn = QPushButton("开始润色/翻译")
        self.translate_btn.clicked.connect(self.startTranslation)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stopTranslation)
        self.stop_btn.setEnabled(False)
        
        # 粘贴按钮
        paste_btn = QPushButton("粘贴")
        paste_btn.clicked.connect(self.pasteText)
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clearInput)
        
        btn_layout.addWidget(self.translate_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(paste_btn)
        btn_layout.addWidget(clear_btn)
        
        input_layout.addLayout(btn_layout)
        
        splitter.addWidget(input_group)
        
        # 输出区域
        output_group = QGroupBox("结果")
        output_layout = QVBoxLayout(output_group)
        
        self.output_text = QPlainTextEdit()
        self.output_text.setPlaceholderText("润色/翻译结果将显示在这里...")
        self.output_text.setReadOnly(True)
        self.output_text.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.output_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.output_text.document().setMaximumBlockCount(0)  # 不限制块数量
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
        
        # 连接目标语言变化的信号
        self.target_lang_combo.currentIndexChanged.connect(self.onTargetLangChanged)
    
    def connectSignals(self):
        """连接信号和槽"""
        self.signals.update_raw_text.connect(self.processAndUpdateText)
        self.signals.finished.connect(self.onTranslationFinished)
        self.signals.error.connect(self.onTranslationError)
        self.signals.reset_stop_button.connect(self.resetStopButton)
    
    def loadModels(self):
        """加载已保存的模型列表和当前已安装的模型"""
        # 从文件加载保存的模型
        saved_models = load_saved_models()
        
        # 获取已安装的模型
        installed_models = get_installed_ollama_models()
        
        # 如果没有检测到模型，提示用户
        if not installed_models:
            QMessageBox.warning(self, "提示", "本地还没有通过 Ollama 部署的大模型，快去安装一个吧！")
            default_models = []
        else:
            # 使用第一个检测到的模型作为默认模型
            default_models = [installed_models[0]]
        
        # 合并所有模型列表，去重
        all_models = list(set(default_models + saved_models + installed_models))
        
        # 填充下拉框
        self.model_combo.clear()
        for model in all_models:
            self.model_combo.addItem(model)
    
    def onTargetLangChanged(self, index):
        """处理目标语言选择变化"""
        selected_data = self.target_lang_combo.currentData()
        self.custom_lang_input.setVisible(selected_data == "custom")
    
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
        models = [self.model_combo.itemText(i) for i in range(self.model_combo.count())]
        save_models(models)
    
    def startTranslation(self):
        """开始翻译/润色"""
        if self.text_handler.is_translating:
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
        """停止翻译/润色"""
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
    
    def onTranslationFinished(self):
        """翻译/润色完成"""
        self.text_handler.is_translating = False
        self.translate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("停止")
    
    def onTranslationError(self, error_msg):
        """翻译/润色出错"""
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
    
    def applyToMainWindow(self):
        """将结果应用到主窗口"""
        text = self.output_text.toPlainText()
        if text and self.parent:
            try:
                # 假设父窗口有output_text属性
                self.parent.output_text.setText(text)
                QMessageBox.information(self, "提示", "已应用到主窗口")
                self.accept()  # 关闭对话框
            except AttributeError:
                QMessageBox.warning(self, "错误", "无法应用到主窗口")
    
    def closeEvent(self, event):
        """关闭窗口时处理"""
        if self.text_handler.is_translating:
            result = QMessageBox.question(
                self, "确认", "翻译/润色任务正在进行，确定要关闭吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if result == QMessageBox.Yes:
                self.text_handler.is_translating = False
                event.accept()
            else:
                event.ignore()
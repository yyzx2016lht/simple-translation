"""主窗口界面"""
import pyperclip
from PySide6.QtCore import Qt, QThreadPool, QSize, QEvent
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QComboBox, QTextEdit, QFrame, 
    QSplitter, QMessageBox, QStatusBar, QToolBar, QStackedWidget
)
from ui.polish.window import AIPolishWidget  # 使用新类名
from config import LANGUAGES, DEFAULT_SOURCE_LANG, DEFAULT_TARGET_LANG
from worker import TranslateWorker


class TranslatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # 设置窗口基本属性
        self.setWindowTitle("现代翻译器")
        self.setMinimumSize(700, 500)
        
        # 创建工具栏
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        
        # 关于按钮
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.showAbout)
        toolbar.addAction(about_action)
        
        # 创建页面切换按钮
        self.translate_action = QAction("文本翻译", self)
        self.translate_action.triggered.connect(self.showTranslatePage)
        toolbar.addAction(self.translate_action)
        
        # AI润色按钮修改为切换页面
        self.polish_action = QAction("AI润色", self)
        self.polish_action.triggered.connect(self.showPolishPage)
        toolbar.addAction(self.polish_action)
        
        self.addToolBar(toolbar)
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建堆叠组件
        self.stack = QStackedWidget()
        
        # 创建翻译页面
        self.translate_page = QWidget()
        self.setupTranslatePage(self.translate_page)
        
        # 创建AI润色页面
        self.polish_page = None  # 初始为None，第一次访问时创建
        
        # 添加翻译页面到堆叠组件
        self.stack.addWidget(self.translate_page)
        
        # 添加堆叠组件到主布局
        main_layout.addWidget(self.stack)
        
        # 默认显示翻译页面
        self.showTranslatePage()
        
        # 设置线程池
        self.threadpool = QThreadPool()
        
    def setupTranslatePage(self, page):
        """设置翻译页面"""
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- 语言选择部分 ---
        self._setupLanguageControls(page_layout)
        
        # --- 创建分割器 ---
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # --- 输入区域 ---
        self._setupInputArea(splitter)
        
        # --- 翻译按钮部分 ---
        translate_container = QWidget()
        translate_layout = QHBoxLayout(translate_container)
        translate_layout.setContentsMargins(0, 5, 0, 5)
        
        translate_layout.addStretch()
        self.translate_btn = QPushButton("翻 译")
        self.translate_btn.setMinimumWidth(120)
        self.translate_btn.setMinimumHeight(30)
        self.translate_btn.clicked.connect(self.translateText)
        translate_layout.addWidget(self.translate_btn)
        translate_layout.addStretch()
        
        page_layout.addWidget(splitter)
        page_layout.addWidget(translate_container)
        
        # --- 输出区域 ---
        self._setupOutputArea(splitter)
        
        # 设置分割器初始大小
        splitter.setSizes([int(self.height() * 0.5), int(self.height() * 0.5)])
        
        # 设置快捷键
        self.input_text.installEventFilter(self)
    
    def setupPolishPage(self):
        """懒加载并设置AI润色页面"""
        # 如果润色页面已经存在，直接返回
        if self.polish_page is not None:
            return
            
        # 获取当前翻译结果作为初始文本
        initial_text = ""
        if hasattr(self, 'output_text'):
            initial_text = self.output_text.toPlainText()
            if initial_text == "翻译中...":
                initial_text = ""
        
        # 创建润色组件
        self.polish_page = AIPolishWidget(self, initial_text)
        
        # 添加到堆叠组件
        self.stack.addWidget(self.polish_page)
    
    def showTranslatePage(self):
        """显示翻译页面"""
        self.stack.setCurrentWidget(self.translate_page)
        self.translate_action.setEnabled(False)
        self.polish_action.setEnabled(True)
        self.setWindowTitle("现代翻译器 - 文本翻译")
        
    def showPolishPage(self):
        """显示AI润色页面"""
        # 确保润色页面已设置
        self.setupPolishPage()
        
        # 更新润色页面的输入文本
        if hasattr(self, 'output_text') and hasattr(self.polish_page, 'input_text'):
            output_text = self.output_text.toPlainText()
            if output_text and output_text != "翻译中...":
                self.polish_page.input_text.setPlainText(output_text)
                
        # 显示润色页面
        self.stack.setCurrentWidget(self.polish_page)
        self.translate_action.setEnabled(True)
        self.polish_action.setEnabled(False)
        self.setWindowTitle("现代翻译器 - AI润色")
    
    # 删除原来的openAIPolish方法，已由showPolishPage替代
    
    def _setupLanguageControls(self, main_layout):
        """设置语言选择控件"""
        lang_frame = QFrame()
        lang_layout = QHBoxLayout(lang_frame)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        
        # 源语言
        src_lang_label = QLabel("源语言:")
        self.src_lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.src_lang_combo.addItem(f"{name} ({code})", code)
        
        # 设置默认源语言
        default_src_index = 0
        for i in range(self.src_lang_combo.count()):
            if self.src_lang_combo.itemData(i) == DEFAULT_SOURCE_LANG:
                default_src_index = i
                break
        self.src_lang_combo.setCurrentIndex(default_src_index)
        
        # 交换按钮
        self.swap_button = QPushButton("⇄")
        self.swap_button.setFixedWidth(40)
        self.swap_button.clicked.connect(self.swapLanguages)
        
        # 目标语言
        tgt_lang_label = QLabel("目标语言:")
        self.tgt_lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            if code != "auto":  # 排除自动选项
                self.tgt_lang_combo.addItem(f"{name} ({code})", code)
        
        # 设置默认目标语言
        default_tgt_index = 0
        for i in range(self.tgt_lang_combo.count()):
            if self.tgt_lang_combo.itemData(i) == DEFAULT_TARGET_LANG:
                default_tgt_index = i
                break
        self.tgt_lang_combo.setCurrentIndex(default_tgt_index)
        
        # 添加语言选择控件到布局
        lang_layout.addWidget(src_lang_label)
        lang_layout.addWidget(self.src_lang_combo, 1)
        lang_layout.addWidget(self.swap_button)
        lang_layout.addWidget(tgt_lang_label)
        lang_layout.addWidget(self.tgt_lang_combo, 1)
        
        main_layout.addWidget(lang_frame)
        
    def _setupInputArea(self, parent):
        """设置输入区域"""
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        # 输入标题栏
        input_header = QFrame()
        input_header_layout = QHBoxLayout(input_header)
        input_header_layout.setContentsMargins(0, 0, 0, 5)
        
        input_label = QLabel("输入文本:")
        input_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        input_header_layout.addWidget(input_label)
        input_header_layout.addStretch()
        
        self.clear_input_btn = QPushButton("清空")
        self.clear_input_btn.clicked.connect(self.clearInput)
        
        self.paste_btn = QPushButton("粘贴")
        self.paste_btn.clicked.connect(self.pasteText)
        
        input_header_layout.addWidget(self.clear_input_btn)
        input_header_layout.addWidget(self.paste_btn)
        
        input_layout.addWidget(input_header)
        
        # 输入文本框
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("在此输入要翻译的文本...")
        input_layout.addWidget(self.input_text)
        
        # 添加输入区域到父容器
        parent.addWidget(input_container)
        
    def _setupOutputArea(self, parent):
        """设置输出区域"""
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 0, 0, 0)
        
        # 输出标题栏
        output_header = QFrame()
        output_header_layout = QHBoxLayout(output_header)
        output_header_layout.setContentsMargins(0, 0, 0, 5)
        
        output_label = QLabel("翻译结果:")
        output_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        output_header_layout.addWidget(output_label)
        output_header_layout.addStretch()
        
        self.clear_output_btn = QPushButton("清空")
        self.clear_output_btn.clicked.connect(self.clearOutput)
        
        self.copy_btn = QPushButton("复制")
        self.copy_btn.clicked.connect(self.copyText)
        
        output_header_layout.addWidget(self.clear_output_btn)
        output_header_layout.addWidget(self.copy_btn)
        
        output_layout.addWidget(output_header)
        
        # 输出文本框
        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("翻译结果将显示在这里...")
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        
        # 添加输出区域到父容器
        parent.addWidget(output_container)
        
    def eventFilter(self, source, event):
        # 检查事件是否是键盘事件
        if event.type() == QEvent.KeyPress:
            # 处理 Ctrl+Enter 快捷键
            if (source is self.input_text and 
                event.key() == Qt.Key_Return and 
                event.modifiers() == Qt.ControlModifier):
                self.translateText()
                return True
        return super().eventFilter(source, event)
        
    def translateText(self):
        source_text = self.input_text.toPlainText().strip()
        
        # 获取语言代码
        source_lang = self.src_lang_combo.currentData()
        target_lang = self.tgt_lang_combo.currentData()
        
        # 基本验证
        if not source_text:
            QMessageBox.warning(self, "提示", "请输入要翻译的文本。")
            return
            
        if source_lang == target_lang and source_lang != "auto":
            QMessageBox.warning(self, "提示", "源语言和目标语言相同。")
            self.output_text.setText(source_text)
            return
            
        # 处理文本分行
        lines = [line for line in source_text.split('\n') if line.strip()]
        if not lines:
            self.output_text.clear()
            return
            
        # 显示"翻译中..."提示
        self.output_text.setText("翻译中...")
        self.statusBar.showMessage("正在翻译...")
        self.translate_btn.setEnabled(False)
        
        # 创建工作线程
        worker = TranslateWorker(lines, source_lang, target_lang)
        worker.signals.finished.connect(self.handleTranslateFinished)
        worker.signals.error.connect(self.handleTranslateError)
        worker.signals.progress.connect(self.handleTranslateProgress)
        
        # 启动线程
        self.threadpool.start(worker)
        
    def handleTranslateFinished(self, result_with_time):
        parts = result_with_time.split("|")
        translation = parts[0]
        elapsed = parts[1]
        
        self.output_text.setText(translation)
        self.statusBar.showMessage(f"翻译完成，耗时: {elapsed}秒")
        self.translate_btn.setEnabled(True)
        
    def handleTranslateError(self, error_msg):
        QMessageBox.critical(self, "错误", error_msg)
        self.output_text.clear()
        self.statusBar.showMessage("翻译失败")
        self.translate_btn.setEnabled(True)
        
    def handleTranslateProgress(self, progress):
        self.statusBar.showMessage(f"翻译进度: {progress}%")
        
    def clearInput(self):
        self.input_text.clear()
        
    def clearOutput(self):
        self.output_text.clear()
        
    def pasteText(self):
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                cursor = self.input_text.textCursor()
                cursor.insertText(clipboard_content)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法访问剪贴板: {e}")
            
    def copyText(self):
        content = self.output_text.toPlainText().strip()
        if content:
            try:
                pyperclip.copy(content)
                self.statusBar.showMessage("已复制到剪贴板", 2000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法复制到剪贴板: {e}")
        else:
            QMessageBox.warning(self, "提示", "输出框中没有内容可复制。")
            
    def swapLanguages(self):
        # 交换源语言和目标语言
        src_data = self.src_lang_combo.currentData()
        tgt_data = self.tgt_lang_combo.currentData()
        
        # 查找对应索引
        new_src_idx = 0
        for i in range(self.src_lang_combo.count()):
            if self.src_lang_combo.itemData(i) == tgt_data:
                new_src_idx = i
                break
                
        new_tgt_idx = 0
        for i in range(self.tgt_lang_combo.count()):
            if self.tgt_lang_combo.itemData(i) == src_data:
                new_tgt_idx = i
                break
                
        # 设置新的语言选择
        self.src_lang_combo.setCurrentIndex(new_src_idx)
        self.tgt_lang_combo.setCurrentIndex(new_tgt_idx)
        
    def showAbout(self):
        QMessageBox.about(self, "关于", 
                         "现代翻译器 v2.0\n\n"
                         "一个简单而美观的翻译应用。\n"
                         "使用PySide6(Qt)构建，支持多种语言翻译。")
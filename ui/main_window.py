"""主窗口界面"""
import pyperclip
from PySide6.QtCore import Qt, QThreadPool, QSize, QEvent, Signal
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QComboBox, QPlainTextEdit, QFrame,  # 改为QPlainTextEdit
    QSplitter, QMessageBox, QStatusBar, QToolBar, QStackedWidget, QSizePolicy
)
from ui.ai_translation.window import AIPolishWidget  # 使用新类名
from config.config import LANGUAGES, DEFAULT_SOURCE_LANG, DEFAULT_TARGET_LANG
from translator.NMT_translator import TranslateWorker
from .settings import SettingsWidget
from ui.ai_translation.utils import is_ollama_available

class TranslatePlainTextEdit(QPlainTextEdit):
    """支持Enter键触发翻译，Shift+Enter换行的纯文本输入框"""
    translateRequested = Signal()
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                # Shift+Enter插入换行
                super().keyPressEvent(event)
            else:
                # Enter触发翻译
                self.translateRequested.emit()
        else:
            # 其他按键正常处理
            super().keyPressEvent(event)


class TranslatorApp(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 添加翻译停止标志
        self.translation_stopped = False
        
        # 初始化线程池
        self.threadpool = QThreadPool()
        
        # 初始化用户界面
        self.initUI()
        
    def initUI(self):
        # 设置窗口基本属性
        self.setWindowTitle("简易翻译器")
        self.setMinimumSize(700, 500)
        
        # 创建工具栏
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        
        # 创建页面切换按钮
        self.translate_action = QAction("文本翻译", self)
        self.translate_action.setCheckable(True)  # 添加这行
        self.translate_action.triggered.connect(self.showTranslatePage)
        toolbar.addAction(self.translate_action)
        
        # AI翻译按钮修改为切换页面
        self.polish_action = QAction("AI翻译", self)
        self.polish_action.setCheckable(True)  # 添加这行
        self.polish_action.triggered.connect(self.showPolishPage)
        toolbar.addAction(self.polish_action)
        
        # 创建设置按钮
        self.settings_btn = QAction("设置", self)
        self.settings_btn.setCheckable(True)  # 添加这行
        self.settings_btn.triggered.connect(self.showSettingsPage)
        toolbar.addAction(self.settings_btn)
        
   
        # 关于按钮放在最右侧
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.showAbout)
        toolbar.addAction(about_action)
        
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
        
        # 创建AI翻译页面
        self.polish_page = None  # 初始为None，第一次访问时创建
        
        # 初始化设置页面
        self.settings_widget = SettingsWidget(self)
        
        # 添加翻译页面到堆叠组件
        self.stack.addWidget(self.translate_page)
        
        # 将设置页面添加到堆叠组件
        self.stack.addWidget(self.settings_widget)
        
        # 添加堆叠组件到主布局
        main_layout.addWidget(self.stack)
        
        # 默认显示翻译页面
        self.showTranslatePage()
        
        # 设置线程池
        self.threadpool = QThreadPool()
        
        # 添加样式表使选中按钮更明显
        self.setStyleSheet("""
            QToolBar QAction:checked { 
                background-color: #007bff; 
                color: white;
                border-radius: 4px;
            }
        """)
        
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
        
        # --- 输出区域 ---
        self._setupOutputArea(splitter)
        
        # 设置分割器初始大小
        splitter.setSizes([int(self.height() * 0.5), int(self.height() * 0.5)])
        
        # 先添加分割器
        page_layout.addWidget(splitter)
        
        # --- 翻译按钮部分（移到splitter后面）---
        translate_container = QWidget()
        translate_container.setObjectName("translate_container")
        translate_layout = QHBoxLayout(translate_container)
        translate_layout.setContentsMargins(0, 5, 0, 5)
        
        translate_layout.addStretch()
        
        # 翻译按钮
        self.translate_btn = QPushButton("翻 译")
        self.translate_btn.setMinimumWidth(120)
        self.translate_btn.setMinimumHeight(30)
        self.translate_btn.clicked.connect(self.translateText)
        translate_layout.addWidget(self.translate_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("停 止")
        self.stop_btn.setMinimumWidth(120)
        self.stop_btn.setMinimumHeight(30)
        self.stop_btn.clicked.connect(self.stopTranslation)
        self.stop_btn.setEnabled(False)  # 初始状态为禁用
        translate_layout.addWidget(self.stop_btn)
        
        translate_layout.addStretch()
        
        # 然后添加按钮容器
        page_layout.addWidget(translate_container)
        
        # 设置快捷键
        self.input_text.translateRequested.connect(self.translateText)
    
    def setupPolishPage(self):
        """懒加载并设置AI翻译页面"""
        # 如果翻译页面已经存在，直接返回
        if self.polish_page is not None:
            return
            
        # 获取当前翻译结果作为初始文本
        initial_text = ""
        if hasattr(self, 'output_text'):
            initial_text = self.output_text.toPlainText()
            if initial_text == "翻译中...":
                initial_text = ""
        
        # 创建翻译组件
        self.polish_page = AIPolishWidget(self, initial_text)
        
        # 添加到堆叠组件
        self.stack.addWidget(self.polish_page)
    
    def showTranslatePage(self):
        """显示翻译页面"""
        self.stack.setCurrentWidget(self.translate_page)
        
        # 更新按钮状态
        self.translate_action.setChecked(True)
        self.polish_action.setChecked(False)
        self.settings_btn.setChecked(False)
        
        # 确保工具栏按钮正确连接
        self.translate_action.triggered.disconnect()
        self.translate_action.triggered.connect(self.showTranslatePage)
        self.polish_action.triggered.disconnect()
        self.polish_action.triggered.connect(self.showPolishPage)
    
    def showPolishPage(self):
        """显示AI翻译页面"""
        
        if not is_ollama_available():
            reply = QMessageBox.warning(
                self,
                "Ollama检测失败",
                "未能检测到Ollama程序。<br><br>"
                "AI翻译功能需要安装并运行Ollama程序。<br>"
                "请前往官网下载：<a href='https://ollama.com/'>https://ollama.com/</a><br><br>"
                "是否仍要继续进入AI翻译页面？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 更新按钮状态
        self.translate_action.setChecked(False)
        self.polish_action.setChecked(True)
        self.settings_btn.setChecked(False)
        # 创建AI翻译窗口组件
        self.polish_widget = AIPolishWidget(self)
        self.stack.addWidget(self.polish_widget)
        self.stack.setCurrentWidget(self.polish_widget)
    
    def showSettingsPage(self):
        """显示设置页面"""
        self.stack.setCurrentWidget(self.settings_widget)
        
        # 更新按钮状态
        self.translate_action.setChecked(False)
        self.polish_action.setChecked(False)
        self.settings_btn.setChecked(True)
        
        self.translate_action.setEnabled(True)
        self.polish_action.setEnabled(True)
    
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
        self.input_text = TranslatePlainTextEdit()  # 改用自定义的纯文本框
        self.input_text.setPlaceholderText("在此输入要翻译的文本...")
        input_layout.addWidget(self.input_text)
        
        # 添加快捷键提示
        shortcut_tip = QLabel("提示: 按Enter开始翻译，按Shift+Enter换行")
        shortcut_tip.setStyleSheet("color: #666; font-size: 10px;")
        input_layout.addWidget(shortcut_tip)
        
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
        self.output_text = QPlainTextEdit()  # 改为QPlainTextEdit
        self.output_text.setPlaceholderText("翻译结果将显示在这里...")
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        
        # 添加输出区域到父容器
        parent.addWidget(output_container)

        
    def translateText(self):
        source_text = self.input_text.toPlainText().strip()
        
        # 获取语言代码
        source_lang = self.src_lang_combo.currentData()
        target_lang = self.tgt_lang_combo.currentData()
        
        # 基本验证
        if not source_text:
            QMessageBox.warning(self, "提示", "请输入要翻译的文本。")
            return
            
        # 处理文本分行
        lines = [line for line in source_text.split('\n') if line.strip()]
        if not lines:
            self.output_text.clear()
            return
            
        # 显示"翻译中..."提示
        self.output_text.setPlainText("翻译中...")  # 改为setPlainText
        self.statusBar.showMessage("正在翻译...")
        self.translate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)  # 启用停止按钮
        
        # 创建工作线程
        worker = TranslateWorker(lines, source_lang, target_lang)
        self.current_worker = worker  # 保存当前工作线程
        worker.signals.finished.connect(self.handleTranslateFinished)
        worker.signals.error.connect(self.handleTranslateError)
        worker.signals.progress.connect(self.handleTranslateProgress)
        
        # 启动线程
        self.threadpool.start(worker)
        
    def stopTranslation(self):
        """停止正在进行的翻译请求"""
        try:
            # 设置标志表示是手动停止的翻译
            self.translation_stopped = True
            
            # 设置停止标志
            if hasattr(self, 'current_worker') and self.current_worker:
                self.current_worker.stop()
                
            # 更新界面状态
            self.translate_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.statusBar.showMessage("翻译已取消")
            self.output_text.setPlainText("翻译已取消")
            
            # 断开当前工作线程的错误信号连接
            if hasattr(self, 'current_worker') and self.current_worker:
                try:
                    self.current_worker.signals.error.disconnect()
                except:
                    pass
            
        except Exception as e:
            print(f"停止翻译时出错: {e}")
        
    def handleTranslateFinished(self, result_with_time):
        parts = result_with_time.split("|")
        translation = parts[0]
        elapsed = parts[1]
        
        self.output_text.setPlainText(translation)
        self.statusBar.showMessage(f"翻译完成，耗时: {elapsed}秒")
        self.translate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)  # 禁用停止按钮
        self.current_worker = None

    def handleTranslateError(self, error_msg):
        # 检查是否是用户手动停止翻译导致的错误
        if hasattr(self, 'translation_stopped') and self.translation_stopped:
            # 如果是手动停止的，不显示错误消息
            self.translation_stopped = False
            return
            
        # 如果不是手动停止，显示错误消息
        QMessageBox.critical(self, "错误", error_msg)
        self.output_text.clear()
        self.statusBar.showMessage("翻译失败")
        self.translate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.current_worker = None
        
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
                         "简易翻译器 v2.0\n\n"
                         "调用Mtranserver服务器实现翻译功能\n"
                         "支持Ollama部署AI模型进行翻译，支持多种语言对齐。\n")
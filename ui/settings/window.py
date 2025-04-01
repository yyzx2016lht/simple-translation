"""设置窗口组件"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFormLayout, QGroupBox, QMessageBox
)

from config_manager import config_manager

class SettingsWidget(QWidget):
    """设置界面组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()
    
    def initUI(self):
        """初始化用户界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 服务器设置组
        server_group = QGroupBox("服务器设置")
        server_layout = QFormLayout(server_group)
        
        # 获取当前配置
        current_base_url = config_manager.config.get("base_url", "")
        current_token = config_manager.config.get("token", "")
        
        # 服务器地址设置
        self.base_url_input = QLineEdit(current_base_url)
        self.base_url_input.setPlaceholderText("如: http://8.138.46.186:8989")
        info_label = QLabel("请输入完整的服务器基础URL")
        info_label.setStyleSheet("color: #666;")
        server_layout.addRow("服务器地址:", self.base_url_input)
        server_layout.addRow("", info_label)
        
        # Token 设置
        self.token_input = QLineEdit(current_token)
        self.token_input.setPlaceholderText("如: yyzx2016lht")
        token_info = QLabel("如果不需要令牌，请留空")
        token_info.setStyleSheet("color: #666;")
        server_layout.addRow("认证令牌:", self.token_input)
        server_layout.addRow("", token_info)
        
        # 完整URL预览
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("color: #0066cc; font-family: monospace;")
        self.update_preview()
        
        # 当输入改变时更新预览
        self.base_url_input.textChanged.connect(self.update_preview)
        self.token_input.textChanged.connect(self.update_preview)
        
        server_layout.addRow("完整URL预览:", self.preview_label)
        
        main_layout.addWidget(server_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        apply_btn = QPushButton("立即应用")
        apply_btn.clicked.connect(self.apply_settings)
        apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_settings)
        
        back_btn = QPushButton("返回")
        back_btn.clicked.connect(self.back_to_main)
        
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addWidget(back_btn)
        btn_layout.addStretch()
        
        main_layout.addLayout(btn_layout)
        main_layout.addStretch()
    
    def update_preview(self):
        """更新URL预览，显示基础API地址"""
        base_url = self.base_url_input.text().strip()
        token = self.token_input.text().strip()
        
        if base_url:
            # 去除尾部斜杠
            base_url = base_url.rstrip("/")
            
            # 显示翻译API的地址 (不包含token)
            full_url = f"{base_url}/translate"
            
            # 额外显示认证信息
            auth_info = "无认证信息" if not token else f"Authorization: {token}"
            self.preview_label.setText(f"{full_url}\n认证头: {auth_info}")
        else:
            self.preview_label.setText("")
    
    def apply_settings(self):
        """应用设置并立即生效"""
        base_url = self.base_url_input.text().strip()
        token = self.token_input.text().strip()  # 确保剔除前后空格
        
        if not base_url:
            QMessageBox.warning(self, "警告", "服务器地址不能为空")
            return
        
        # 更新配置
        if config_manager.update_server_config(base_url, token):
            QMessageBox.information(self, "成功", "设置已更新并立即生效")
            # 更新预览以显示最新状态
            self.update_preview()
        else:
            QMessageBox.critical(self, "错误", "保存设置失败")
    
    def reset_settings(self):
        """恢复默认设置"""
        self.base_url_input.setText("http://localhost:8989")
        self.token_input.clear()
        self.update_preview()
    
    def back_to_main(self):
        """返回主页面"""
        if self.parent and hasattr(self.parent, 'showTranslatePage'):
            self.parent.showTranslatePage()
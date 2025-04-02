"""配置管理器，负责动态管理和更新配置"""
import os
import json
import requests
import sys
import threading

class ConfigManager:
    """配置管理器单例类"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 使用用户数据目录存储配置
        app_data_dir = self._get_app_data_dir()
        self.config_file = os.path.join(app_data_dir, "config_user.json")
        self.default_config = {
            "base_url": "http://8.138.46.186:8989/",
            "token": "yyzx2016lht"
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # 其余代码不变...
        self.config = self.load_config()
        self.update_urls()
        self.session = requests.Session()
        self.init_session()
        self._initialized = True

    def _get_app_data_dir(self):
        """获取应用数据目录"""
        if hasattr(sys, '_MEIPASS'):  # 如果是PyInstaller打包的应用
            # 使用用户的AppData目录
            app_data = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), '简易翻译器')
        else:
            # 开发环境，使用项目目录下的config文件夹
            app_data = os.path.dirname(os.path.abspath(__file__))
        
        # 确保目录存在
        os.makedirs(app_data, exist_ok=True)
        return app_data
    
    def load_config(self):
        """加载用户配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件出错: {e}")
        return self.default_config.copy()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件出错: {e}")
            return False
    
    def init_session(self):
        """初始化网络会话"""
        try:
            print("初始化网络会话...")
            
            # 创建带更多重试和更长超时的适配器
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=3  # 增加重试次数
            )
            self.session = requests.Session()
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
            
            # 设置默认超时 (连接超时, 读取超时)
            self.session.timeout = (10, 30)  # 10秒连接超时，30秒读取超时
            
            # 获取并设置token
            token = self.config.get("token", "").strip()
            if token:
                self.session.headers.update({"Authorization": token})
                
            # 预热连接 - 发送一个HEAD请求
            self._warm_up_connection()
        except Exception as e:
            print(f"初始化网络会话失败: {str(e)}")
            # 确保session总是存在
            self.session = requests.Session()

    def _warm_up_connection(self):
        """预热连接 - 在后台线程中进行，不阻塞UI"""
        def do_warmup():
            try:
                # 尝试连接服务器
                self.session.head(
                    self.BASE_URL, 
                    timeout=(5, 5),  # 短超时，仅用于预热
                    allow_redirects=False
                )
                print("服务器连接预热完成")
            except Exception as e:
                # 忽略错误，这只是预热
                print(f"服务器连接预热失败: {e}")
        
        # 在后台线程中进行预热
        thread = threading.Thread(target=do_warmup)
        thread.daemon = True
        thread.start()
    
    def update_urls(self):
        """更新 API URLs，不再在URL中添加token"""
        base_url = self.config.get("base_url", "http://8.138.46.186:8989/")
        
        # 去除尾部斜杠
        base_url = base_url.rstrip("/")
        
        # 设置基础URL (不再包含token)
        self.BASE_URL = base_url
        
        # 所有API端点URL不再包含token参数
        self.SINGLE_TRANSLATE_URL = f"{self.BASE_URL}/translate"
        self.BATCH_TRANSLATE_URL = f"{self.BASE_URL}/translate/batch"
    
    def update_server_config(self, base_url, token=""):
        """更新服务器配置并立即生效"""
        # 确保token是字符串并去除空格
        token = str(token).strip()
        
        # 更新配置
        self.config["base_url"] = base_url
        self.config["token"] = token
        
        # 更新URLs
        self.update_urls()
        
        # 更新会话认证头
        if token:
            self.session.headers.update({"Authorization": token})
        else:
            # 如果没有token，删除认证头
            if "Authorization" in self.session.headers:
                del self.session.headers["Authorization"]
        
        # 保存到文件
        return self.save_config()
    
    def get_session(self):
        """获取会话对象，并设置认证头"""
        # 获取token
        token = self.config.get("token", "").strip()
        
        # 如果有token，设置认证头
        if token:
            self.session.headers.update({"Authorization": token})
        else:
            # 如果没有token，删除认证头
            if "Authorization" in self.session.headers:
                del self.session.headers["Authorization"]
                
        return self.session

# 创建全局配置管理器实例
config_manager = ConfigManager()
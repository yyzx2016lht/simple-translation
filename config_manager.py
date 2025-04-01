"""配置管理器，负责动态管理和更新配置"""
import os
import json
import requests

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
            
        self.config_file = os.path.join(os.path.dirname(__file__), "config_user.json")
        self.default_config = {
            "base_url": "http://localhost:8989",
            "token": ""
        }
        
        # 加载配置
        self.config = self.load_config()
        
        # 初始化 API URLs
        self.update_urls()
        
        # 初始化网络会话
        self.session = requests.Session()
        self.init_session()
        
        self._initialized = True
    
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
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=2
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def update_urls(self):
        """更新 API URLs，不再在URL中添加token"""
        base_url = self.config.get("base_url", "http://localhost:8989")
        
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
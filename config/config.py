"""翻译应用的配置文件"""
# 将相对导入改为绝对导入
from config.config_manager import config_manager  # 移除前面的点

# --- API配置 ---
# 从配置管理器获取动态URL
BASE_URL = config_manager.BASE_URL
SINGLE_TRANSLATE_URL = config_manager.SINGLE_TRANSLATE_URL
BATCH_TRANSLATE_URL = config_manager.BATCH_TRANSLATE_URL

# --- 网络配置 ---
# 使用配置管理器的会话
session = config_manager.get_session()

# --- 性能配置 ---
MAX_BATCH_SIZE = 40  # 每批处理的最大行数
MAX_WORKERS = 10     # 最大并行工作线程数
TIMEOUT_SINGLE = 1   # 单行请求超时（秒）
TIMEOUT_BATCH = 1   # 批量请求基础超时（秒）

# --- 语言配置 ---
LANGUAGES = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "ru": "Russian",
    "es": "Spanish",
}
DEFAULT_SOURCE_LANG = "en"
DEFAULT_TARGET_LANG = "zh"

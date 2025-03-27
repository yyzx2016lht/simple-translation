"""翻译应用的配置文件"""
import requests

# --- API配置 ---
BASE_URL = "http://localhost:8989"
SINGLE_TRANSLATE_URL = f"{BASE_URL}/translate"
BATCH_TRANSLATE_URL = f"{BASE_URL}/translate/batch"

# --- 网络配置 ---
# 创建全局会话对象
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=2
)
session.mount('http://', adapter)
session.mount('https://', adapter)

# --- 性能配置 ---
MAX_BATCH_SIZE = 40  # 每批处理的最大行数
MAX_WORKERS = 10     # 最大并行工作线程数
TIMEOUT_SINGLE = 0.5   # 单行请求超时（秒）
# 注意：TIMEOUT_BATCH 不再直接使用，已改为动态计算
# 保留此变量是为了兼容性，实际值由 api.py 中的 calculate_timeout 函数动态计算
TIMEOUT_BATCH = 0.01    # 批量请求基础超时（秒），实际超时会动态调整

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

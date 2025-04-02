"""翻译API接口封装"""
import json
import requests
from config.config import session, SINGLE_TRANSLATE_URL, BATCH_TRANSLATE_URL, TIMEOUT_SINGLE, TIMEOUT_BATCH

def calculate_timeout(texts):
    """根据文本量动态计算超时时间"""
    # 统计总字符数
    total_chars = sum(len(text) for text in texts)
    # 计算行数
    num_lines = len(texts)
    
    # 基础超时设置
    base_timeout = 1  # 最小超时1秒
    
    # 根据字符数和行数计算额外超时
    # 每1000个字符增加1秒超时
    char_timeout = (total_chars / 1000) * 1
    # 每10行增加0.3秒超时
    line_timeout = (num_lines / 10) * 0.3
    
    # 计算总超时，最小1秒，最大10秒
    timeout = min(10.0, max(base_timeout, base_timeout + char_timeout + line_timeout))
    
    return timeout

def translate_single(text, source_lang, target_lang):
    """翻译单行文本"""
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'ModernTranslator/2.0',
        'Accept-Encoding': 'gzip, deflate'
    }
    
    payload = {
        "from": source_lang,
        "to": target_lang,
        "text": text
    }
    
    response = session.post(
        SINGLE_TRANSLATE_URL, 
        headers=headers, 
        json=payload, 
        timeout=TIMEOUT_SINGLE
    )
    response.raise_for_status()
    
    result_data = response.json()
    if "result" in result_data:
        return result_data["result"]
    else:
        raise ValueError("API响应格式错误，缺少 'result' 字段")

def translate_batch(texts, source_lang, target_lang):
    """翻译多行文本"""
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'ModernTranslator/2.0',
        'Accept-Encoding': 'gzip, deflate'
    }
    
    payload = {
        "from": source_lang,
        "to": target_lang,
        "texts": texts
    }
    
    # 使用动态计算的超时时间而不是固定值
    dynamic_timeout = calculate_timeout(texts)
    
    response = session.post(
        BATCH_TRANSLATE_URL,
        headers=headers,
        json=payload,
        timeout=dynamic_timeout  # 使用动态超时
    )
    response.raise_for_status()
    
    result_data = response.json()
    if "results" in result_data and isinstance(result_data["results"], list):
        return result_data["results"]
    else:
        raise ValueError("API响应格式错误，缺少 'results' 列表")

def get_friendly_error_message(exception):
    """返回用户友好的错误消息"""
    if isinstance(exception, requests.exceptions.ConnectionError):
        return f"网络错误: 无法连接到翻译服务器"
    elif isinstance(exception, requests.exceptions.Timeout):
        return "超时错误: 连接翻译服务器超时/检查是否语言设置错误"
    elif isinstance(exception, requests.exceptions.RequestException):
        return f"请求错误: {exception}"
    elif isinstance(exception, json.JSONDecodeError):
        return "格式错误: 无法解析服务器返回的响应"
    elif isinstance(exception, ValueError):
        return f"API 错误: {exception}"
    else:
        return f"未知错误: {exception}"
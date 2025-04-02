"""翻译API接口封装"""
import json
import requests
import os
# 修改为直接使用config_manager，不通过config.py
from config.config_manager import config_manager

def calculate_timeout(texts):
    """根据文本量动态计算超时时间"""
    # 统计总字符数
    total_chars = sum(len(text) for text in texts)
    # 计算行数
    num_lines = len(texts)
    
    # 基础超时设置
    base_timeout = 5  # 最小超时5秒，从1秒增加到5秒
    
    # 根据字符数和行数计算额外超时
    # 每1000个字符增加1.5秒超时，从1秒增加到1.5秒
    char_timeout = (total_chars / 1000) * 1.5
    # 每10行增加0.5秒超时，从0.3秒增加到0.5秒
    line_timeout = (num_lines / 10) * 0.5
    
    # 计算总超时，最小5秒，最大30秒
    # 将最大超时从10秒增加到30秒
    timeout = min(30.0, max(base_timeout, base_timeout + char_timeout + line_timeout))
    
    # 为第一次请求额外增加超时时间（首次连接往往需要更长时间）
    first_request_flag = os.path.join(os.environ.get('TEMP', '.'), '.translator_first_req')
    if not os.path.exists(first_request_flag):
        # 首次请求超时翻倍
        timeout = timeout * 2
        # 创建标记文件
        try:
            with open(first_request_flag, 'w') as f:
                f.write('1')
        except:
            pass
    
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
    
    # 为较长文本动态增加超时时间
    dynamic_timeout = max(10, len(text) / 500)
    
    # 为首次请求增加超时时间
    first_request_flag = os.path.join(os.environ.get('TEMP', '.'), '.translator_first_req')
    if not os.path.exists(first_request_flag):
        dynamic_timeout = dynamic_timeout * 2
    
    try:
        # 直接使用config_manager的session和URL
        response = config_manager.session.post(
            config_manager.SINGLE_TRANSLATE_URL,  # 直接使用config_manager的URL
            headers=headers, 
            json=payload, 
            timeout=dynamic_timeout
        )
        response.raise_for_status()
        
        result_data = response.json()
        if "result" in result_data:
            return result_data["result"]
        else:
            raise ValueError("API响应格式错误，缺少 'result' 字段")
    except requests.exceptions.Timeout:
        # 超时情况下，创建首次请求标记文件（以避免重复首次请求检测）
        try:
            with open(first_request_flag, 'w') as f:
                f.write('1')
        except:
            pass
        raise

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
    
    # 直接使用config_manager的session和URL
    response = config_manager.session.post(
        config_manager.BATCH_TRANSLATE_URL,  # 直接使用config_manager的URL
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
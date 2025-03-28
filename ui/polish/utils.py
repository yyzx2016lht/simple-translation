"""AI润色窗口使用的工具函数和常量"""
import os
import json
import subprocess
from pathlib import Path

# 语言映射字典
LANGUAGE_MAPPING = {
    "Auto": "自动检测", 
    "Chinese": "中文", 
    "English": "英文", 
    "Japanese": "日文", 
    "Korean": "韩文", 
    "French": "法文", 
    "German": "德文", 
    "Russian": "俄文", 
    "Spanish": "西班牙文"
}

def get_installed_ollama_models():
    """获取当前电脑已安装的Ollama模型列表"""
    try:
        # 执行ollama list命令
        result = subprocess.run(["ollama", "list"], 
                               capture_output=True, 
                               text=True, 
                               check=True)
        
        # 解析输出结果
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:  # 只有标题行，没有模型
            return []
            
        # 需要排除的非大模型列表
        exclude_models = [
            'nomic-embed-text:latest', 
            'nomic-embed-text',
        ]
            
        # 提取模型名称（第一列）
        models = []
        for line in lines[1:]:  # 跳过标题行
            parts = line.split()
            if parts:  # 确保行不为空
                model_name = parts[0]  # 第一列是模型名称
                # 检查是否为需要排除的模型
                if model_name not in exclude_models and not any(model_name.startswith(prefix) for prefix in ["nomic-embed"]):
                    models.append(model_name)
                
        return models
    except subprocess.CalledProcessError:
        print("执行ollama list命令失败")
        return []
    except Exception as e:
        print(f"获取Ollama模型列表出错: {e}")
        return []

def load_saved_models():
    """加载用户保存的自定义模型列表"""
    models_file = Path(os.path.expanduser("~")) / ".translator_models.json"
    
    if models_file.exists():
        try:
            with open(models_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取模型列表出错: {e}")
    
    return []

def save_models(models):
    """保存模型列表到用户目录"""
    models_file = Path(os.path.expanduser("~")) / ".translator_models.json"
    
    try:
        with open(models_file, 'w', encoding='utf-8') as f:
            json.dump(models, f)
        return True
    except Exception as e:
        print(f"保存模型列表出错: {e}")
        return False

def process_thinking_tags(text, debug_mode=False):
    """处理大模型输出中的<think></think>标签"""
    import re
    
    # 存储原始长度用于调试
    original_length = len(text)
    
    # 先处理完整的思考标签 - 使用非贪婪模式
    pattern = r'<think>.*?</think>'
    processed = re.sub(pattern, '', text, flags=re.DOTALL)
    
    # 处理未闭合的思考标签
    open_tag_pos = processed.find('<think>')
    if open_tag_pos >= 0:
        # 只保留<think>之前的内容，加上思考提示
        processed = processed[:open_tag_pos] + ' [🤔思考中...] '
    
    # 调试信息
    if debug_mode:
        print(f"原始文本长度: {original_length}, 处理后长度: {len(processed)}")
        if original_length != len(processed):
            print(f"移除了 {original_length - len(processed)} 个字符的思考内容")
    
    return processed
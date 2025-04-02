"""AI窗口使用的工具函数和常量"""
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

def is_ollama_available():
    """检查ollama命令是否可用"""
    try:
        import subprocess
        result = subprocess.run(
            ["ollama", "--version"], 
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0
    except Exception:
        return False

def get_installed_ollama_models():
    """获取已安装的Ollama模型列表，包含错误处理"""
    # 要排除的模型
    excluded_models = ["nomic-embed-text:latest"]
    
    try:
        import subprocess
        import sys
        
        # 执行命令
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, 
            text=True,
            creationflags=creation_flags,
            timeout=10  # 添加超时防止卡死
        )
        
        if result.returncode != 0:
            print(f"命令执行失败: {result.stderr}")
            return []
        
        # 解析命令输出
        output = result.stdout
        models = []
        
        # 按行分割输出
        lines = output.strip().split('\n')
        
        # 跳过第一行（标题行）
        if len(lines) > 1:
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                # 分割行，获取模型名称（第一列）
                parts = line.split()
                if parts:
                    model_name = parts[0].strip()
                    
                    # 排除特定模型
                    if model_name not in excluded_models:
                        models.append(model_name)
        
        return models
        
    except FileNotFoundError:
        # 处理Ollama不存在的情况
        print("未找到Ollama程序，请确保已安装")
        return []
    except subprocess.TimeoutExpired:
        print("命令执行超时")
        return []
    except Exception as e:
        print(f"获取Ollama模型出错: {str(e)}")
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
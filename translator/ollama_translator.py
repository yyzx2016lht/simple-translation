"""
Ollama本地翻译模块 - 精简版
专注于高质量文本翻译，保留原始格式
"""

import time
import tiktoken
import ollama
from ollama import Options

class OllamaTranslator:
    def __init__(self, model):
        """初始化翻译器"""
        self.model = model
        # 使用通用编码器作为token计数的方法
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoding = None
        
    def translate(self, text, source_lang=None, target_lang=None, 
                 temperature=0.7, stream=False, update_callback=None):
        """翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言（可选）
            target_lang: 目标语言
            temperature: 生成温度
            stream: 是否使用流式输出
            update_callback: 流式输出的回调函数
            
        Returns:
            翻译后的文本
        """
        if not text or not text.strip():
            return ""
            
        # 设置默认目标语言
        if not target_lang:
            target_lang = "Chinese"
        
        # 构建翻译提示词
        prompt = self._build_translation_prompt(text, source_lang, target_lang)
        
        # 设置模型选项
        options = Options(temperature=temperature)
        
        try:
            if stream:
                return self._stream_translation(prompt, options, update_callback)
            else:
                return self._direct_translation(prompt, options, update_callback)
                
        except Exception as e:
            error_msg = f"翻译出错: {str(e)}"
            if update_callback:
                update_callback(f"[翻译错误] {str(e)}")
            return f"[翻译错误] {str(e)}"
    
    def _stream_translation(self, prompt, options, update_callback):
        """流式翻译处理"""
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options=options,
            stream=True,
            keep_alive=5
        )
        
        chunks = ""
        for chunk in response:
            content = chunk["message"]["content"]
            chunks += content
            
            if update_callback:
                continue_generation = update_callback(chunks)
                if continue_generation is False:
                    break
        
        return chunks
    
    def _direct_translation(self, prompt, options, update_callback):
        """直接翻译处理"""
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options=options,
            stream=False,
            keep_alive=5
        )
        
        translated_text = response["message"]["content"]
        
        if update_callback:
            update_callback(translated_text)
            
        return translated_text
    
    def _build_translation_prompt(self, text, source_lang, target_lang):
        """构建简化的翻译提示词"""
        # 提示词
        base_prompt = f"""
你是一位精通多语言的专业翻译专家。请根据以下规则处理文本：


**翻译要求**：
1. 完全保留原文格式：段落结构、换行、列表、标点符号和空格。
2. 直接输出翻译结果，不添加任何解释、注释或附加内容。
3. 保持专业术语准确性，尤其涉及技术、学术或专业领域。
4. 翻译需自然流畅，符合{target_lang}的表达习惯和语法规则。
5. 若用户误将目标语言设为与原文同语言，请优先触发规则1的提示。
请记住，你的目标是直接输出翻译结果，不添加任何解释、注释或附加内容。
<text>
{text}
</text>
请直接提供处理结果，无需任何前言或说明：

"""

# 后续处理流程由您决定（比如对比检测源语言）




        # 基于源语言添加可选提示
        if source_lang:
            base_prompt = base_prompt.replace("将下面文本", f"将下面{source_lang}文本")
        
        return base_prompt


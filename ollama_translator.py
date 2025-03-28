"""
Ollama本地翻译模块
专注于高质量文本翻译，保留原始格式
"""

import re
import time
import tiktoken
import ollama
from ollama import Options

class OllamaTranslator:
    def __init__(self, model="qwen2.5:7b"):
        """初始化翻译器
        
        Args:
            model: 使用的Ollama模型名称，默认使用qwen2.5:7b
        """
        self.model = model
        # 使用gpt-4编码器作为token计数的近似值
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-4")
        except:
            # 如果加载失败，尝试使用cl100k_base作为后备
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
    def translate(self, text, source_lang=None, target_lang=None, 
                 temperature=0.7, stream=False, max_tokens=None, update_callback=None):
        """翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言（可选）
            target_lang: 目标语言
            temperature: 生成温度
            stream: 是否使用流式输出
            max_tokens: 最大输出token数
            update_callback: 流式输出的回调函数，接收当前累积文本作为参数
            
        Returns:
            翻译后的文本
        """
        if not text or not text.strip():
            return ""
            
        # 设置默认目标语言
        if not target_lang:
            target_lang = "Chinese"
        
        # 估算输入token数量
        estimated_tokens = len(self.encoding.encode(text))
        
        # 获取模型上下文窗口大小限制（估算值）
        model_context_limit = self._get_model_context_limit()
        
        # 如果文本太长，需要分段处理
        if estimated_tokens > model_context_limit * 0.7:  # 留30%空间给模型回复
            return self._translate_long_text(
                text, source_lang, target_lang, temperature, stream, max_tokens, update_callback
            )
        else:
            # 文本在模型处理能力范围内，直接翻译
            return self._translate_with_prompt(
                text, source_lang, target_lang, temperature, stream, max_tokens, update_callback
            )
    
    def _get_model_context_limit(self):
        """获取当前模型的上下文窗口大小限制（估算值）"""
        # 基于模型名称估算上下文窗口大小
        model_name = self.model.lower()
        
        if "llama-3" in model_name or "llama3" in model_name:
            if "8b" in model_name:
                return 8192
            elif "70b" in model_name:
                return 8192
        elif "qwen2" in model_name:
            if "7b" in model_name:
                return 32768
            elif "72b" in model_name:
                return 32768
        elif "deepseek" in model_name:
            return 8192
        elif "phi3" in model_name:
            return 4096
        elif "yi" in model_name:
            return 4096
        elif "gemma" in model_name:
            return 8192
        
        # 默认安全值
        return 4000
    
    def _translate_long_text(self, text, source_lang, target_lang, temperature, stream, max_tokens, update_callback):
        """处理超长文本翻译，采用智能分段并保持连贯性"""
        # 使用更智能的分段方法
        segments = self._smart_segment_text(text)
        
        # 存储所有翻译结果
        all_results = []
        
        # 记录累计翻译字符数，用于流式输出时的进度展示
        total_translated = 0
        
        # 逐段翻译，并在每段开始时提供上下文提示
        for i, segment in enumerate(segments):
            # 如果不是第一段，添加上下文提示
            context_prompt = ""
            if i > 0 and all_results:
                # 添加前一段的最后一部分作为上下文
                last_result = all_results[-1]
                context_length = min(200, len(last_result))  # 取最后200个字符作为上下文
                context = last_result[-context_length:]
                context_prompt = f"以下是前文的结尾部分，请确保翻译与之连贯：\n\"{context}\"\n\n现在继续翻译："
            
            # 为每个片段创建专门的回调函数
            if stream and update_callback:
                def segment_callback(current_text):
                    if not stream or not update_callback:
                        return True
                    
                    # 将当前段的翻译与之前的结果合并，以展示完整进度
                    combined_text = "".join(all_results) + current_text
                    return update_callback(combined_text)
            else:
                segment_callback = None
            
            # 翻译当前段落
            segment_result = self._translate_with_prompt(
                segment, 
                source_lang, 
                target_lang, 
                temperature, 
                stream if i == len(segments) - 1 else False,  # 只对最后一段使用流式输出
                max_tokens,
                segment_callback,
                context_prompt
            )
            
            # 保存结果
            all_results.append(segment_result)
            
            # 更新总翻译
            total_translated += len(segment)
            
            # 如果不是流式输出但有回调函数，更新总进度
            if not stream and update_callback:
                combined_result = "".join(all_results)
                update_callback(combined_result)
        
        # 合并所有翻译结果
        final_result = "".join(all_results)
        
        # 再次调用回调函数，确保UI更新到最终状态
        if update_callback:
            update_callback(final_result)
            
        return final_result
    
    def _smart_segment_text(self, text, max_tokens=2000):
        """智能分段文本，尽量保持语义完整性
        
        相比简单的字符数切分，这个方法尝试在句子或段落边界进行切分，
        并且确保每个片段都有足够的上下文。
        """
        # 估算每个字符平均的token数
        chars_per_token = len(text) / max(1, len(self.encoding.encode(text)))
        
        # 计算每个片段的大致字符数
        max_chars = int(max_tokens * chars_per_token * 0.85)  # 留15%余量
        
        # 如果文本小于最大字符数，直接返回
        if len(text) <= max_chars:
            return [text]
        
        # 尝试按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        
        segments = []
        current_segment = ""
        
        for para in paragraphs:
            # 如果段落本身超过最大字符数，需要再分割
            if len(para) > max_chars:
                # 添加当前累积的段落
                if current_segment:
                    segments.append(current_segment)
                    current_segment = ""
                
                # 分割大段落
                para_segments = self._split_large_paragraph(para, max_chars)
                segments.extend(para_segments)
            
            # 如果添加当前段落会超过最大字符数，先保存当前片段
            elif len(current_segment) + len(para) + 2 > max_chars:  # +2 for newlines
                segments.append(current_segment)
                current_segment = para
            
            # 否则将段落添加到当前片段
            else:
                if current_segment:
                    current_segment += "\n\n" + para
                else:
                    current_segment = para
        
        # 添加最后一个片段
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _split_large_paragraph(self, paragraph, max_chars):
        """分割大段落，尽量在句子边界处分割"""
        # 定义句子结束的模式
        sent_end_pattern = r'(?<=[。！？.!?])'
        
        # 尝试按句子分割
        sentences = re.split(sent_end_pattern, paragraph)
        
        # 过滤空句子并重新添加句子结束符号
        processed_sentences = []
        for i, sent in enumerate(sentences):
            if not sent.strip():
                continue
                
            # 如果不是最后一个句子，且不以标点结尾，添加句号
            if i < len(sentences) - 1 and not re.search(r'[。！？.!?]$', sent):
                sent += "。"
                
            processed_sentences.append(sent)
        
        segments = []
        current_segment = ""
        
        for sent in processed_sentences:
            # 如果句子本身超过最大字符数，按固定长度分割
            if len(sent) > max_chars:
                if current_segment:
                    segments.append(current_segment)
                    current_segment = ""
                
                # 简单地按固定长度分割超长句子
                for i in range(0, len(sent), max_chars):
                    segments.append(sent[i:i+max_chars])
            
            # 如果添加当前句子会超过最大字符数，先保存当前片段
            elif len(current_segment) + len(sent) > max_chars:
                segments.append(current_segment)
                current_segment = sent
            
            # 否则将句子添加到当前片段
            else:
                current_segment += sent
        
        # 添加最后一个片段
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _translate_with_prompt(self, text, source_lang, target_lang, temperature, 
                              stream, max_tokens, update_callback, context_prompt=""):
        """使用优化的提示词进行翻译"""
        # 构建优化的提示词
        prompt = self._build_translation_prompt(text, source_lang, target_lang, context_prompt)
        
        # 设置模型选项
        options = Options(
            temperature=temperature,
        )
        
        try:
            start_time = time.time()
            
            if stream:
                # 流式输出模式
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
                    chunks += content  # 累积内容
                    
                    # 调用回调函数更新UI
                    if update_callback:
                        continue_generation = update_callback(chunks)
                        if continue_generation is False:
                            print("检测到停止信号，中断生成")
                            break
                    else:
                        print(content, end="", flush=True)
                        
                    # 检查token上限
                    if max_tokens and len(self.encoding.encode(chunks)) > max_tokens:
                        break
                
                # 只有在没有回调函数时才打印换行
                if not update_callback:
                    print()
                
                translated_text = chunks
            else:
                # 非流式模式
                response = ollama.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    options=options,
                    stream=False,
                    keep_alive=5
                )
                translated_text = response["message"]["content"]
                
                # 如果提供了回调函数，也调用一次（为了统一接口）
                if update_callback:
                    update_callback(translated_text)
            
            # 添加后处理步骤，移除可能的标签
            if "qwen2.5" in self.model.lower():
                translated_text = self._clean_qwen_output(translated_text)
            
            # 计算token和性能（调试用）
            input_token = len(self.encoding.encode(prompt))
            output_token = len(self.encoding.encode(translated_text))
            elapsed = time.time() - start_time
            
            # 只在没有回调函数时打印性能信息
            if not update_callback:
                print(f"翻译耗时: {elapsed:.2f}秒, 速度: {output_token/elapsed:.1f} token/s")
                
            return translated_text
            
        except Exception as e:
            error_msg = f"翻译出错: {str(e)}"
            print(error_msg)
            
            # 如果有回调函数，也通知UI出错了
            if update_callback:
                update_callback(f"[翻译错误] {str(e)}")
                
            return f"[翻译错误] {str(e)}"
    
    def _build_translation_prompt(self, text, source_lang, target_lang, context_prompt=""):
        """构建优化的翻译提示词"""
        # 检查是否为 qwen2.5 模型
        is_qwen = "qwen2.5" in self.model.lower()
        
        # 针对 qwen2.5 使用不同的文本标记方式
        if is_qwen:
            text_marker_start = '"""'
            text_marker_end = '"""'
        else:
            text_marker_start = "<text>"
            text_marker_end = "</text>"
        
        # 基础提示词
        base_prompt = f"""你是一位精通多语言的专业翻译专家。请将下面标记的文本准确翻译成{target_lang}。

翻译要求：
1. 完全保留原文的格式，包括段落结构、换行、列表、标点符号和空格
2. 直接输出翻译结果，不添加任何解释、注释或附加内容
3. 保持专业术语的准确性，尤其是技术文档、学术内容或专业领域的表述
4. 翻译应自然流畅，符合{target_lang}的表达习惯和语法规则
5. 如果源语言与目标语言相同，则对文本进行润色和改进，但保持原意不变

{context_prompt}

{text_marker_start}
{text}
{text_marker_end}

请直接提供{target_lang}翻译结果，无需任何前言或说明："""

        # 基于源语言添加可选提示
        if source_lang:
            base_prompt = base_prompt.replace("将下面标记的文本", 
                                             f"将下面标记的{source_lang}文本")
        
        return base_prompt

    def _clean_qwen_output(self, text):
        """清理 qwen2.5 模型输出中可能存在的标签"""
        # 移除可能的 <text> 和 </text> 标签
        cleaned = re.sub(r'<text>|</text>', '', text)
        # 移除可能的三重引号
        cleaned = re.sub(r'"""', '', cleaned)
        return cleaned.strip()


# 简单使用示例
if __name__ == "__main__":
    translator = OllamaTranslator(model="qwen2.5:7b")
    
    # 测试单行文本翻译
    text = "Hello, world! This is a test of the Ollama translation system."
    result = translator.translate(text, target_lang="Chinese", stream=True)
    print(f"\n翻译结果: {result}")
    
    # 测试多行文本翻译
    text2 = """
    The outline establishes seven major tasks for the new era of language work: "vigorously promoting and popularizing the national common language and writing," "advancing the standardization, standardization and informatization of language and writing," "strengthening supervision, inspection and service of language and writing social applications," "improving the language and writing application ability of citizens," "scientifically protecting ethnic languages and writings," "carrying forward and spreading excellent Chinese culture," and "strengthening the rule of law in language and writing." It defines six key areas of work and sixteen aspects of measures: "promotion and popularization," "infrastructure," "supervision and service," "capacity improvement," "scientific protection," and "cultural inheritance." It proposes eight innovative and safeguard measures, including "innovative concepts and ideas," "innovative working mechanisms," "innovative management services," and "expanding opening up," "strengthening talent protection," "improving scientific research level," "strengthening publicity," and "ensuring funding."
    """
    result2 = translator.translate(text2, target_lang="Chinese", stream=False)
    print(f"\n翻译结果: {result2}")
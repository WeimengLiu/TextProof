"""文本校对服务"""
from typing import Dict, Any, Optional
import sys
import os
import logging

from models.factory import ModelAdapterFactory
from models.base import BaseModelAdapter
from models.exceptions import ConnectionError as ModelConnectionError, ServiceUnavailableError
from utils.text_splitter import TextSplitter
from utils.prompt_manager import prompt_manager
from utils.pycorrector_wrapper import correct_sentence as pycorrector_correct_sentence
import config

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

logger = logging.getLogger(__name__)


class CorrectionService:
    """文本校对服务"""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ):
        """
        初始化校对服务
        
        Args:
            provider: 模型提供商
            model_name: 模型名称
            chunk_size: 分段大小（如果为None，Ollama会自动使用ollama_chunk_size）
            chunk_overlap: 分段重叠大小（如果为None，Ollama会自动使用ollama_chunk_overlap）
        """
        # 记录提供商，后续可根据不同provider应用不同策略
        self.provider = (provider or config.settings.default_model_provider).lower()
        self.adapter: BaseModelAdapter = ModelAdapterFactory.create_adapter(
            provider=provider,
            model_name=model_name
        )
        
        # 如果是Ollama且未显式指定chunk_size，使用Ollama专用配置
        if provider and provider.lower() == "ollama":
            if chunk_size is None:
                chunk_size = config.settings.ollama_chunk_size
                logger.info("[CorrectionService] Using Ollama-specific chunk_size: %d", chunk_size)
            if chunk_overlap is None:
                chunk_overlap = config.settings.ollama_chunk_overlap
                logger.info("[CorrectionService] Using Ollama-specific chunk_overlap: %d", chunk_overlap)
            # 保存 Ollama 的 chunk_size，用于控制每句话的最大长度上限
            self.ollama_max_sentence_length = chunk_size
        else:
            self.ollama_max_sentence_length = None
        
        self.splitter = TextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.prompt = prompt_manager.get_prompt(provider=self.provider)
    
    def _split_by_sentences(self, text: str, max_length: Optional[int] = None) -> tuple:
        """
        按句分割文本（针对 Ollama 小模型，逐句处理）
        
        分割规则：
        1. 优先按换行符分割（每行作为一句）
        2. 如果某一行超过 max_length，才按句号、感叹号、问号等标点进一步分割
        3. 如果分割后仍超过 max_length，按逗号、分号分割
        4. 如果仍超过 max_length，强制按字符数分割
        5. 保留空行和标点符号
        
        Args:
            text: 待分割的文本
            max_length: 每句话的最大长度上限（字符数），None 表示不限制
        
        Returns:
            (sentences_list, line_endings_list): 句子列表和对应的换行符列表
        """
        import re
        
        if not text:
            return ([], [])
        
        def _split_by_punctuation(text: str, max_len: int) -> list:
            """按句号、感叹号、问号分割，如果超过 max_len 则进一步分割"""
            if max_len is None or len(text) <= max_len:
                return [text]
            
            result = []
            # 按句号、问号、感叹号分割，保留标点
            parts = re.split(r'([。！？])', text)
            current_sentence = ''
            
            for part in parts:
                if part in ['。', '！', '？']:
                    if current_sentence:
                        full_sentence = current_sentence + part
                        if len(full_sentence) <= max_len:
                            result.append(full_sentence)
                        else:
                            # 超过限制，先按逗号、分号分割
                            result.extend(_split_by_comma(current_sentence, max_len))
                            result.append(part)
                        current_sentence = ''
                    else:
                        result.append(part)
                elif part.strip():
                    test_sentence = current_sentence + part
                    if len(test_sentence) <= max_len:
                        current_sentence = test_sentence
                    else:
                        # 添加当前部分
                        if current_sentence:
                            result.append(current_sentence)
                        # 如果 part 本身超过限制，按逗号分割或强制分割
                        if len(part) > max_len:
                            result.extend(_split_by_comma(part, max_len))
                        else:
                            current_sentence = part
            
            if current_sentence:
                result.append(current_sentence)
            
            return result if result else [text]
        
        def _split_by_comma(text: str, max_len: int) -> list:
            """按逗号、分号分割，如果仍超过则强制分割"""
            if max_len is None or len(text) <= max_len:
                return [text]
            
            result = []
            parts = re.split(r'([，；])', text)
            current_part = ''
            
            for part in parts:
                if part in ['，', '；']:
                    if current_part:
                        test_sentence = current_part + part
                        if len(test_sentence) <= max_len:
                            result.append(test_sentence)
                            current_part = ''
                        else:
                            # 当前部分超过限制，强制分割
                            if current_part:
                                result.extend(_force_split(current_part, max_len))
                            result.append(part)
                            current_part = ''
                    else:
                        result.append(part)
                elif part.strip():
                    test_sentence = current_part + part
                    if len(test_sentence) <= max_len:
                        current_part = test_sentence
                    else:
                        if current_part:
                            result.append(current_part)
                        if len(part) > max_len:
                            result.extend(_force_split(part, max_len))
                        else:
                            current_part = part
            
            if current_part:
                result.append(current_part)
            
            return result if result else [text]
        
        def _force_split(text: str, max_len: int) -> list:
            """强制按字符数分割"""
            if max_len is None or len(text) <= max_len:
                return [text]
            result = []
            for i in range(0, len(text), max_len):
                result.append(text[i:i + max_len])
            return result
        
        # 优先按换行符分割（每行作为一句）
        lines = text.split('\n')
        sentences = []
        line_endings = []  # 记录每个句子后面是否有换行符
        
        for line_idx, line in enumerate(lines):
            line = line.rstrip()  # 去行尾空白以减少 token，保留左侧缩进
            if not line.strip():
                # 空行：作为单独一句（空字符串）
                sentences.append('')
                line_endings.append('\n' if line_idx < len(lines) - 1 else '')
                continue
            
            # 检查这一行是否超过 max_length
            if max_length is None or len(line) <= max_length:
                # 不超过限制，整行作为一句
                sentences.append(line)
                line_endings.append('\n' if line_idx < len(lines) - 1 else '')
            else:
                # 超过限制，按句号、感叹号、问号等标点分割
                split_sentences = _split_by_punctuation(line, max_length)
                for i, s in enumerate(split_sentences):
                    sentences.append(s)
                    # 只有最后一个句子后面才有换行符
                    if i < len(split_sentences) - 1:
                        line_endings.append('')  # 中间分割的句子，无换行
                    else:
                        line_endings.append('\n' if line_idx < len(lines) - 1 else '')
        
        # 确保 sentences 和 line_endings 长度一致
        while len(line_endings) < len(sentences):
            line_endings.append('')
        
        return (sentences, line_endings) if sentences else ([text], [''])
    
    async def correct_text(
        self,
        text: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        校对文本
        
        Args:
            text: 待校对的文本
            progress_callback: 进度回调函数 (current, total) -> None
            
        Returns:
            包含校对结果的字典
        """
        text_length = len(text)

        # Ollama 专用：按句/按行逐句处理（适合小模型如 14B）
        if self.provider == "ollama":
            max_sentence_length = self.ollama_max_sentence_length or config.settings.ollama_chunk_size
            logger.info("[CorrectionService] Using sentence-by-sentence mode for Ollama (text length: %d, max sentence length: %d)", text_length, max_sentence_length)
            sentences, line_endings = self._split_by_sentences(text, max_length=max_sentence_length)
            total_sentences = len(sentences)
            
            if total_sentences == 0:
                return {
                    "original": text,
                    "corrected": text,
                    "chunks_processed": 0,
                    "total_chunks": 0
                }
            
            logger.info("[CorrectionService] Split into %d sentences for Ollama processing", total_sentences)
            
            corrected_sentences = []
            failed_sentences = []
            consecutive_failures = 0
            max_consecutive_failures = 3
            
            for i, sentence in enumerate(sentences):
                # 跳过空行
                if not sentence.strip():
                    corrected_sentences.append(sentence)
                    if progress_callback:
                        progress_callback(i + 1, total_sentences)
                    continue
                
                sentence_length = len(sentence)
                logger.info("[CorrectionService] Processing sentence %d/%d (length: %d)", i+1, total_sentences, sentence_length)
                logger.debug("[CorrectionService] Sentence %d preview: %s...", i+1, sentence[:50])
                
                try:
                    # 若开启预纠错，先经 pycorrector 一轮再送 Ollama
                    input_for_ollama = sentence
                    if getattr(config.settings, "ollama_use_pycorrector", True):
                        input_for_ollama = await pycorrector_correct_sentence(sentence)
                    corrected_sentence = await self.adapter.correct_text_with_retry(
                        input_for_ollama,
                        self.prompt,
                        max_retries=config.settings.max_retries,
                        retry_delay=config.settings.retry_delay
                    )
                    corrected_sentences.append(corrected_sentence)
                    consecutive_failures = 0
                    
                    if progress_callback:
                        progress_callback(i + 1, total_sentences)
                        
                except ModelConnectionError as e:
                    error_msg = str(e)
                    logger.error("[CorrectionService] Connection error at sentence %d/%d: %s", i+1, total_sentences, error_msg)
                    corrected_sentences.append(sentence)
                    failed_sentences.append({
                        "chunk_index": i + 1,
                        "error": error_msg
                    })
                    # 连接错误时停止
                    for j in range(i + 1, total_sentences):
                        corrected_sentences.append(sentences[j])
                        failed_sentences.append({
                            "chunk_index": j + 1,
                            "error": f"因连接错误跳过处理: {error_msg}"
                        })
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    consecutive_failures += 1
                    logger.warning("[CorrectionService] Sentence %d/%d failed: %s", i+1, total_sentences, error_msg)
                    corrected_sentences.append(sentence)  # 使用原文
                    failed_sentences.append({
                        "chunk_index": i + 1,
                        "error": error_msg
                    })
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error("[CorrectionService] Too many consecutive failures (%d), stopping", consecutive_failures)
                        for j in range(i + 1, total_sentences):
                            corrected_sentences.append(sentences[j])
                            failed_sentences.append({
                                "chunk_index": j + 1,
                                "error": "因连续失败跳过处理"
                            })
                        break
            
            # 按原换行结构拼接（保留换行符）
            corrected_parts = []
            for i, corrected_sentence in enumerate(corrected_sentences):
                corrected_parts.append(corrected_sentence)
                if i < len(line_endings):
                    corrected_parts.append(line_endings[i])
            corrected_text = ''.join(corrected_parts)
            
            if len(failed_sentences) == total_sentences and total_sentences > 0:
                error_messages = [f"句子 {fs['chunk_index']}: {fs['error']}" for fs in failed_sentences[:5]]
                error_msg = f"所有句子校对失败: {'; '.join(error_messages)}"
                if len(failed_sentences) > 5:
                    error_msg += f" ... (共{len(failed_sentences)}个失败)"
                raise RuntimeError(error_msg)
            
            return {
                "original": text,
                "corrected": corrected_text,
                "chunks_processed": len([s for s in corrected_sentences if s.strip()]),
                "total_chunks": total_sentences,
                "failed_chunks": len(failed_sentences),
                "has_failures": len(failed_sentences) > 0,
                "failure_details": failed_sentences if failed_sentences else None
            }

        # 对于 OpenAI / DeepSeek 这类“云端大模型”，单个章节在一定长度以内时可以直接整段发送，
        # 避免不必要的分段和合并，保持上下文完整性。
        # 注意：这里只对「已按章节切好、且单章长度不超阈值」的情况有效。
        fast_providers = {"openai", "deepseek"}
        # 经验值：1 个中文字符约 1-2 tokens，默认阈值见 config.settings.fast_provider_max_chars
        max_direct_length = getattr(config.settings, "fast_provider_max_chars", 10000)

        if self.provider in fast_providers and text_length <= max_direct_length:
            logger.info(
                "[CorrectionService] Using direct full-text correction for provider=%s, length=%d "
                "(threshold=%d, no chunking)",
                self.provider,
                text_length,
                max_direct_length,
            )
            try:
                corrected_full = await self.adapter.correct_text_with_retry(
                    text,
                    self.prompt,
                    max_retries=config.settings.max_retries,
                    retry_delay=config.settings.retry_delay,
                )

                # 进度回调：视为单个chunk
                if progress_callback:
                    progress_callback(1, 1)

                return {
                    "original": text,
                    "corrected": corrected_full,
                    "chunks_processed": 1,
                    "total_chunks": 1,
                    "failed_chunks": 0,
                    "has_failures": False,
                    "failure_details": None,
                }
            except Exception as e:
                # 如果整段调用失败，回退到正常分段策略，保证鲁棒性
                logger.warning(
                    "[CorrectionService] Direct full-text correction failed for provider=%s, "
                    "will fallback to chunked mode: %s",
                    self.provider,
                    str(e),
                )

        # 正常分段流程
        chunks = self.splitter.split(text)
        total_chunks = len(chunks)
        
        if total_chunks == 0:
            return {
                "original": text,
                "corrected": text,
                "chunks_processed": 0,
                "total_chunks": 0
            }
        
        # 校对每个片段
        corrected_chunks = []
        failed_chunks = []
        adapter_name = self.adapter.__class__.__name__
        consecutive_failures = 0  # 连续失败计数
        max_consecutive_failures = 3  # 最大连续失败次数，超过则停止
        
        logger.info("[CorrectionService] Starting correction of %d chunks", total_chunks)
        logger.info("[CorrectionService] Using adapter: %s", adapter_name)
        logger.info("[CorrectionService] Max retries: %d, Retry delay: %.1f", config.settings.max_retries, config.settings.retry_delay)
        
        for i, chunk in enumerate(chunks):
            chunk_length = len(chunk)
            chunk_preview = chunk[:50] + "..." if len(chunk) > 50 else chunk
            logger.info("[CorrectionService] Processing chunk %d/%d (length: %d)", i+1, total_chunks, chunk_length)
            logger.debug("[CorrectionService] Chunk %d preview: %s", i+1, chunk_preview)
            
            try:
                corrected_chunk = await self.adapter.correct_text_with_retry(
                    chunk,
                    self.prompt,
                    max_retries=config.settings.max_retries,
                    retry_delay=config.settings.retry_delay
                )
                corrected_length = len(corrected_chunk)
                logger.info("[CorrectionService] Chunk %d/%d corrected successfully (original: %d, corrected: %d)", i+1, total_chunks, chunk_length, corrected_length)
                corrected_chunks.append(corrected_chunk)
                consecutive_failures = 0  # 重置连续失败计数
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(i + 1, total_chunks)
            except ModelConnectionError as e:
                # 连接错误：立即停止处理，所有chunk都视为失败
                error_msg = str(e)
                logger.error("[CorrectionService] Connection error detected at chunk %d/%d: %s", i+1, total_chunks, error_msg)
                logger.error("[CorrectionService] Stopping processing due to connection error - all chunks will be marked as failed")
                
                # 当前失败的chunk
                corrected_chunks.append(chunks[i])
                failed_chunks.append({
                    "chunk_index": i + 1,
                    "error": error_msg
                })
                
                # 为剩余chunk填充原文并标记为失败
                for j in range(i + 1, total_chunks):
                    corrected_chunks.append(chunks[j])
                    failed_chunks.append({
                        "chunk_index": j + 1,
                        "error": f"因连接错误跳过处理: {error_msg}"
                    })
                
                # 连接错误时，所有chunk都失败，直接跳出循环
                break
            except ServiceUnavailableError as e:
                # 服务不可用：记录但继续尝试，如果连续失败则停止
                error_msg = str(e)
                consecutive_failures += 1
                logger.warning("[CorrectionService] Service unavailable at chunk %d/%d: %s", i+1, total_chunks, error_msg)
                logger.warning("[CorrectionService] Consecutive failures: %d/%d", consecutive_failures, max_consecutive_failures)
                
                corrected_chunks.append(chunk)
                failed_chunks.append({
                    "chunk_index": i + 1,
                    "error": error_msg
                })
                print(f"片段 {i+1}/{total_chunks} 服务不可用，使用原文: {error_msg}")
                
                # 如果连续失败次数过多，停止处理
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("[CorrectionService] Too many consecutive failures (%d), stopping processing", consecutive_failures)
                    # 为剩余chunk填充原文并标记为失败
                    for j in range(i + 1, total_chunks):
                        corrected_chunks.append(chunks[j])
                        failed_chunks.append({
                            "chunk_index": j + 1,
                            "error": f"因连续服务不可用跳过处理"
                        })
                    break
            except Exception as e:
                # 其他错误：记录但继续处理
                error_msg = str(e)
                consecutive_failures += 1
                logger.error("[CorrectionService] Chunk %d/%d correction failed: %s", i+1, total_chunks, error_msg)
                logger.error("[CorrectionService] Using original text for chunk %d", i+1)
                logger.warning("[CorrectionService] Consecutive failures: %d/%d", consecutive_failures, max_consecutive_failures)
                
                corrected_chunks.append(chunk)
                failed_chunks.append({
                    "chunk_index": i + 1,
                    "error": error_msg
                })
                print(f"片段 {i+1}/{total_chunks} 校对失败，使用原文: {error_msg}")
                
                # 如果连续失败次数过多，停止处理
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("[CorrectionService] Too many consecutive failures (%d), stopping processing", consecutive_failures)
                    # 为剩余chunk填充原文并标记为失败
                    for j in range(i + 1, total_chunks):
                        corrected_chunks.append(chunks[j])
                        failed_chunks.append({
                            "chunk_index": j + 1,
                            "error": f"因连续失败跳过处理"
                        })
                    break
        
        # 合并结果
        corrected_text = self.splitter.merge(corrected_chunks)
        
        # 如果所有片段都失败，抛出异常
        if len(failed_chunks) == total_chunks and total_chunks > 0:
            error_messages = [f"片段 {fc['chunk_index']}: {fc['error']}" for fc in failed_chunks]
            error_msg = f"所有片段校对失败: {'; '.join(error_messages)}"
            raise RuntimeError(error_msg)
        
        return {
            "original": text,
            "corrected": corrected_text,
            "chunks_processed": len(corrected_chunks),
            "total_chunks": total_chunks,
            "failed_chunks": len(failed_chunks),
            "has_failures": len(failed_chunks) > 0,
            "failure_details": failed_chunks if failed_chunks else None
        }
    
    async def health_check(self) -> bool:
        """检查服务是否可用"""
        return await self.adapter.health_check()

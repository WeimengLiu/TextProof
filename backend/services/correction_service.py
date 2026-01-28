"""文本校对服务"""
from typing import Dict, Any, Optional
import sys
import os
import logging

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models.factory import ModelAdapterFactory
from models.base import BaseModelAdapter
from models.exceptions import ConnectionError as ModelConnectionError, ServiceUnavailableError
from utils.text_splitter import TextSplitter
from utils.prompt_manager import prompt_manager
import config

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
                logger.info(f"[CorrectionService] Using Ollama-specific chunk_size: {chunk_size}")
            if chunk_overlap is None:
                chunk_overlap = config.settings.ollama_chunk_overlap
                logger.info(f"[CorrectionService] Using Ollama-specific chunk_overlap: {chunk_overlap}")
        
        self.splitter = TextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.prompt = prompt_manager.get_prompt()
    
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
        
        logger.info(f"[CorrectionService] Starting correction of {total_chunks} chunks")
        logger.info(f"[CorrectionService] Using adapter: {adapter_name}")
        logger.info(f"[CorrectionService] Max retries: {config.settings.max_retries}, Retry delay: {config.settings.retry_delay}")
        
        for i, chunk in enumerate(chunks):
            chunk_length = len(chunk)
            chunk_preview = chunk[:50] + "..." if len(chunk) > 50 else chunk
            logger.info(f"[CorrectionService] Processing chunk {i+1}/{total_chunks} (length: {chunk_length})")
            logger.debug(f"[CorrectionService] Chunk {i+1} preview: {chunk_preview}")
            
            try:
                corrected_chunk = await self.adapter.correct_text_with_retry(
                    chunk,
                    self.prompt,
                    max_retries=config.settings.max_retries,
                    retry_delay=config.settings.retry_delay
                )
                corrected_length = len(corrected_chunk)
                logger.info(f"[CorrectionService] Chunk {i+1}/{total_chunks} corrected successfully (original: {chunk_length}, corrected: {corrected_length})")
                corrected_chunks.append(corrected_chunk)
                consecutive_failures = 0  # 重置连续失败计数
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(i + 1, total_chunks)
            except ModelConnectionError as e:
                # 连接错误：立即停止处理，所有chunk都视为失败
                error_msg = str(e)
                logger.error(f"[CorrectionService] Connection error detected at chunk {i+1}/{total_chunks}: {error_msg}")
                logger.error(f"[CorrectionService] Stopping processing due to connection error - all chunks will be marked as failed")
                
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
                logger.warning(f"[CorrectionService] Service unavailable at chunk {i+1}/{total_chunks}: {error_msg}")
                logger.warning(f"[CorrectionService] Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                
                corrected_chunks.append(chunk)
                failed_chunks.append({
                    "chunk_index": i + 1,
                    "error": error_msg
                })
                print(f"片段 {i+1}/{total_chunks} 服务不可用，使用原文: {error_msg}")
                
                # 如果连续失败次数过多，停止处理
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"[CorrectionService] Too many consecutive failures ({consecutive_failures}), stopping processing")
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
                logger.error(f"[CorrectionService] Chunk {i+1}/{total_chunks} correction failed: {error_msg}")
                logger.error(f"[CorrectionService] Using original text for chunk {i+1}")
                logger.warning(f"[CorrectionService] Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                
                corrected_chunks.append(chunk)
                failed_chunks.append({
                    "chunk_index": i + 1,
                    "error": error_msg
                })
                print(f"片段 {i+1}/{total_chunks} 校对失败，使用原文: {error_msg}")
                
                # 如果连续失败次数过多，停止处理
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"[CorrectionService] Too many consecutive failures ({consecutive_failures}), stopping processing")
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

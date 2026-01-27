"""文本校对服务"""
from typing import List, Dict, Any, Optional
import sys
import os

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models.factory import ModelAdapterFactory
from models.base import BaseModelAdapter
from utils.text_splitter import TextSplitter
from utils.prompt_manager import prompt_manager
import config
import asyncio


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
            chunk_size: 分段大小
            chunk_overlap: 分段重叠大小
        """
        self.adapter: BaseModelAdapter = ModelAdapterFactory.create_adapter(
            provider=provider,
            model_name=model_name
        )
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
        # 分段
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
        for i, chunk in enumerate(chunks):
            try:
                corrected_chunk = await self.adapter.correct_text_with_retry(
                    chunk,
                    self.prompt,
                    max_retries=config.settings.max_retries,
                    retry_delay=config.settings.retry_delay
                )
                corrected_chunks.append(corrected_chunk)
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(i + 1, total_chunks)
            except Exception as e:
                # 如果校对失败，使用原文
                corrected_chunks.append(chunk)
                print(f"片段 {i+1}/{total_chunks} 校对失败，使用原文: {str(e)}")
        
        # 合并结果
        corrected_text = self.splitter.merge(corrected_chunks)
        
        return {
            "original": text,
            "corrected": corrected_text,
            "chunks_processed": len(corrected_chunks),
            "total_chunks": total_chunks
        }
    
    async def health_check(self) -> bool:
        """检查服务是否可用"""
        return await self.adapter.health_check()

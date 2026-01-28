"""模型适配器基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


class BaseModelAdapter(ABC):
    """模型适配器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def correct_text(self, text: str, prompt: str) -> str:
        """
        校对文本
        
        Args:
            text: 待校对的文本
            prompt: 校对提示词
            
        Returns:
            校对后的文本
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """检查模型服务是否可用"""
        pass
    
    async def correct_text_with_retry(
        self, 
        text: str, 
        prompt: str, 
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> str:
        """
        带重试的文本校对
        
        Args:
            text: 待校对的文本
            prompt: 校对提示词
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            校对后的文本
            
        Raises:
            Exception: 所有重试失败后抛出异常
        """
        last_error = None
        adapter_name = self.__class__.__name__
        
        logger.info(f"[{adapter_name} Retry] Starting correction with max_retries={max_retries}, retry_delay={retry_delay}")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[{adapter_name} Retry] Attempt {attempt + 1}/{max_retries}")
                result = await self.correct_text(text, prompt)
                logger.info(f"[{adapter_name} Retry] Success on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"[{adapter_name} Retry] Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    delay = retry_delay * (attempt + 1)
                    logger.info(f"[{adapter_name} Retry] Waiting {delay} seconds before retry...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{adapter_name} Retry] All {max_retries} attempts failed")
                    raise last_error
        
        raise last_error

"""OpenAI模型适配器"""
from typing import Dict, Any
from openai import AsyncOpenAI
from models.base import BaseModelAdapter
from models.exceptions import ConnectionError as ModelConnectionError, ServiceUnavailableError
import os
import logging

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI API适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model_name = config.get("model_name", "gpt-4-turbo-preview")
    
    async def correct_text(self, text: str, prompt: str) -> str:
        """使用OpenAI API校对文本"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,  # 低温度保证稳定性
                max_tokens=len(text) + 500  # 允许略微增加长度
            )
            
            result = response.choices[0].message.content.strip()
            return result
        except Exception as e:
            error_msg = str(e)
            error_lower = error_msg.lower()
            
            # 检查是否是连接错误
            if any(keyword in error_lower for keyword in ['connection', 'connect', 'network', 'dns', 'timeout', 'unreachable']):
                logger.error(f"[OpenAI] Connection error detected: {error_msg}")
                raise ModelConnectionError(f"OpenAI API连接失败: {error_msg}")
            # 检查是否是服务不可用错误
            elif any(keyword in error_lower for keyword in ['503', '502', '504', 'service unavailable', 'bad gateway']):
                logger.error(f"[OpenAI] Service unavailable: {error_msg}")
                raise ServiceUnavailableError(f"OpenAI API服务不可用: {error_msg}")
            else:
                raise Exception(f"OpenAI API调用失败: {error_msg}")
    
    async def health_check(self) -> bool:
        """检查OpenAI服务是否可用"""
        try:
            await self.client.models.list()
            return True
        except:
            return False

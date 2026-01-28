"""DeepSeek模型适配器"""
from typing import Dict, Any
from openai import AsyncOpenAI
from models.base import BaseModelAdapter
from models.exceptions import ConnectionError as ModelConnectionError, ServiceUnavailableError
import os
import logging

logger = logging.getLogger(__name__)


class DeepSeekAdapter(BaseModelAdapter):
    """DeepSeek API适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        api_key = config.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        base_url = config.get("base_url") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model_name = config.get("model_name", "deepseek-chat")
    
    async def correct_text(self, text: str, prompt: str) -> str:
        """使用DeepSeek API校对文本"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.0,  # 降低到0.0，更严格遵循指令，减少创造性替换
                max_tokens=len(text) + 500
            )
            
            raw_response = response.choices[0].message.content
            response_text = raw_response.strip()
            
            logger.info(f"[DeepSeek] Raw response length: {len(raw_response)} characters")
            logger.info(f"[DeepSeek] Raw response preview: {raw_response[:300]}...")
            
            # 清理可能包含的提示词标记（类似 Ollama 的处理）
            markers_to_remove = [
                "待校对文本：",
                "校对后的文本：",
                "校对后：",
                "精校后：",
                "结果：",
                "校对结果：",
            ]
            
            # 首先清理开头的标记
            for marker in markers_to_remove:
                if response_text.startswith(marker):
                    response_text = response_text[len(marker):].strip()
                    logger.info(f"[DeepSeek] Removed leading marker: {marker}")
                    break
            
            # 检查是否在文本中间出现标记（可能是模型重复了提示词）
            for marker in markers_to_remove:
                if marker in response_text:
                    last_idx = response_text.rfind(marker)
                    if last_idx >= 0:
                        before_marker = response_text[:last_idx].strip()
                        after_marker = response_text[last_idx + len(marker):].strip()
                        
                        if len(after_marker) > len(before_marker) * 0.8 or len(before_marker) < 50:
                            response_text = after_marker
                            logger.info(f"[DeepSeek] Removed middle marker: {marker}")
                            break
            
            logger.info(f"[DeepSeek] Final response length: {len(response_text)} characters")
            logger.info(f"[DeepSeek] Final response preview: {response_text[:200]}...")
            
            return response_text
        except Exception as e:
            error_msg = str(e)
            error_lower = error_msg.lower()
            
            # 检查是否是连接错误
            if any(keyword in error_lower for keyword in ['connection', 'connect', 'network', 'dns', 'timeout', 'unreachable']):
                logger.error(f"[DeepSeek] Connection error detected: {error_msg}")
                raise ModelConnectionError(f"DeepSeek API连接失败: {error_msg}")
            # 检查是否是服务不可用错误
            elif any(keyword in error_lower for keyword in ['503', '502', '504', 'service unavailable', 'bad gateway']):
                logger.error(f"[DeepSeek] Service unavailable: {error_msg}")
                raise ServiceUnavailableError(f"DeepSeek API服务不可用: {error_msg}")
            else:
                raise Exception(f"DeepSeek API调用失败: {error_msg}")
    
    async def health_check(self) -> bool:
        """检查DeepSeek服务是否可用"""
        try:
            await self.client.models.list()
            return True
        except:
            return False

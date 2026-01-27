"""DeepSeek模型适配器"""
from typing import Dict, Any
from openai import AsyncOpenAI
from models.base import BaseModelAdapter
import os


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
                temperature=0.1,
                max_tokens=len(text) + 500
            )
            
            result = response.choices[0].message.content.strip()
            return result
        except Exception as e:
            raise Exception(f"DeepSeek API调用失败: {str(e)}")
    
    async def health_check(self) -> bool:
        """检查DeepSeek服务是否可用"""
        try:
            await self.client.models.list()
            return True
        except:
            return False

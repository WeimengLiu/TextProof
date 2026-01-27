"""Ollama模型适配器"""
from typing import Dict, Any
import httpx
from models.base import BaseModelAdapter
import os


class OllamaAdapter(BaseModelAdapter):
    """Ollama本地模型适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        base_url = config.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.base_url = base_url.rstrip("/")
        self.model_name = config.get("model_name", "llama2")
        self.timeout = config.get("timeout", 300.0)
    
    async def correct_text(self, text: str, prompt: str) -> str:
        """使用Ollama API校对文本"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 构建完整的提示词
                full_prompt = f"{prompt}\n\n待校对文本：\n{text}\n\n校对后的文本："
                
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": len(text) + 500
                        }
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
        except httpx.TimeoutException:
            raise Exception(f"Ollama API调用超时（{self.timeout}秒）")
        except Exception as e:
            raise Exception(f"Ollama API调用失败: {str(e)}")
    
    async def health_check(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except:
            return False

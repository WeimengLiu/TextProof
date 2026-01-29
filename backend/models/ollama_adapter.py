"""Ollama模型适配器"""
from typing import Dict, Any
import httpx
from models.base import BaseModelAdapter
from models.exceptions import ConnectionError as ModelConnectionError, ServiceUnavailableError
import os
import logging

logger = logging.getLogger(__name__)


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
        url = f"{self.base_url}/api/generate"
        text_length = len(text)
        text_preview = text[:100] + "..." if len(text) > 100 else text
        
        logger.info("[Ollama] 开始校对请求")
        logger.info("[Ollama] Base URL: %s", self.base_url)
        logger.info("[Ollama] Model: %s", self.model_name)
        logger.info("[Ollama] Request URL: %s", url)
        logger.info("[Ollama] Text length: %d characters", text_length)
        logger.info("[Ollama] Text preview: %s", text_preview)
        logger.info("[Ollama] Timeout: %.1f seconds", self.timeout)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 构建完整的提示词
                full_prompt = f"{prompt}\n\n待校对文本：\n{text}\n\n校对后的文本："
                prompt_length = len(full_prompt)
                
                # num_predict 是 tokens 数，不是字符数
                # 对于中文，1个字符约等于1-2个tokens，为了安全起见，我们按2倍计算
                # 同时需要预留足够的空间给输出（至少和输入一样长，加上一些缓冲）
                # 如果 num_predict 太小，模型输出会被截断
                estimated_tokens = text_length * 2  # 输入文本的token估算
                num_predict = max(estimated_tokens + 1000, 2048)  # 至少2048，确保有足够输出空间
                
                logger.info("[Ollama] Estimated input tokens: %d, num_predict: %d", estimated_tokens, num_predict)
                
                request_payload = {
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": num_predict
                    }
                }
                
                logger.info("[Ollama] Request payload size: %d characters", prompt_length)
                logger.info("[Ollama] Request payload preview: %s...", full_prompt[:200])
                logger.info("[Ollama] Sending POST request to %s", url)
                
                response = await client.post(url, json=request_payload)
                
                logger.info("[Ollama] Response status code: %d", response.status_code)
                logger.info("[Ollama] Response headers: %s", dict(response.headers))
                
                response.raise_for_status()
                
                result = response.json()
                raw_response = result.get("response", "")
                response_text = raw_response.strip()
                
                logger.info("[Ollama] Raw response length: %d characters", len(raw_response))
                logger.info("[Ollama] Raw response preview: %s...", raw_response[:300])
                
                # 清理可能包含的提示词标记
                # 移除开头的"待校对文本："、"校对后的文本："等标记
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
                        break  # 只处理第一个匹配的标记
                
                # 检查是否在文本中间出现标记（可能是模型重复了提示词）
                # 这种情况通常是因为模型没有正确理解指令，返回了包含提示词的完整文本
                for marker in markers_to_remove:
                    if marker in response_text:
                        # 找到最后一个标记的位置（通常真正的结果在最后）
                        last_idx = response_text.rfind(marker)
                        if last_idx >= 0:
                            before_marker = response_text[:last_idx].strip()
                            after_marker = response_text[last_idx + len(marker):].strip()
                            
                            # 如果标记后的内容明显更长，使用标记后的内容
                            # 或者如果标记前的内容很短（可能是重复的提示词），也使用标记后的内容
                            if len(after_marker) > len(before_marker) * 0.8 or len(before_marker) < 50:
                                response_text = after_marker
                                break
                
                response_length = len(response_text)
                
                logger.info("[Ollama] Response received successfully")
                logger.info("[Ollama] Response text length: %d characters", response_length)
                logger.info("[Ollama] Response preview: %s...", response_text[:200])
                
                # 检查响应是否异常短（可能是被截断或清理逻辑有问题）
                if response_length < text_length * 0.5:
                    logger.warning(
                        f"[Ollama] Warning: Response length ({response_length}) is much shorter than "
                        f"input length ({text_length}). This might indicate truncation or cleaning issue."
                    )
                    logger.warning("[Ollama] Full response: %s", response_text)
                
                return response_text
                
        except httpx.TimeoutException as e:
            error_msg = f"Ollama API调用超时（{self.timeout}秒）"
            logger.error("[Ollama] %s", error_msg)
            logger.error("[Ollama] Timeout exception: %s", str(e))
            logger.error("[Ollama] Request URL: %s", url)
            raise Exception(error_msg)
        except httpx.ConnectError as e:
            error_msg = f"Ollama API连接失败: 无法连接到 {self.base_url}"
            logger.error("[Ollama] %s", error_msg)
            logger.error("[Ollama] Connection error: %s", str(e))
            logger.error("[Ollama] Request URL: %s", url)
            logger.error("[Ollama] Base URL: %s", self.base_url)
            raise ModelConnectionError(error_msg)
        except httpx.HTTPStatusError as e:
            error_msg = f"Ollama API返回错误状态码: {e.response.status_code}"
            logger.error("[Ollama] %s", error_msg)
            logger.error("[Ollama] Response status: %d", e.response.status_code)
            logger.error("[Ollama] Response text: %s", e.response.text[:500])
            logger.error("[Ollama] Request URL: %s", url)
            raise Exception(f"{error_msg} - {e.response.text[:200]}")
        except Exception as e:
            error_msg = f"Ollama API调用失败: {str(e)}"
            logger.error("[Ollama] %s", error_msg)
            logger.error("[Ollama] Exception type: %s", type(e).__name__)
            logger.error("[Ollama] Exception details: %s", str(e))
            logger.error("[Ollama] Request URL: %s", url)
            logger.error("[Ollama] Base URL: %s", self.base_url)
            raise Exception(error_msg)
    
    async def health_check(self) -> bool:
        """检查Ollama服务是否可用"""
        url = f"{self.base_url}/api/tags"
        logger.info("[Ollama Health] Checking health at %s", url)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                status_ok = response.status_code == 200
                logger.info("[Ollama Health] Status code: %d, Health: %s", response.status_code, status_ok)
                if status_ok:
                    try:
                        result = response.json()
                        logger.info("[Ollama Health] Available models: %s", result.get('models', []))
                    except:
                        pass
                return status_ok
        except Exception as e:
            logger.error("[Ollama Health] Health check failed: %s", str(e))
            logger.error("[Ollama Health] URL: %s", url)
            return False

"""Ollama模型适配器"""
from typing import Dict, Any
import httpx
import os
import logging

from models.base import BaseModelAdapter
from models.exceptions import ConnectionError as ModelConnectionError

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
        """使用Ollama API校对文本（使用 /api/chat 端点，messages 格式）"""
        url = f"{self.base_url}/api/chat"
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
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ]
                estimated_tokens = text_length * 2
                num_predict = max(estimated_tokens + 1000, 2048)

                logger.info("[Ollama] Estimated input tokens: %d, num_predict: %d", estimated_tokens, num_predict)

                request_payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": num_predict,
                    },
                }

                logger.info("[Ollama] Request payload: system prompt length: %d, user content length: %d", len(prompt), text_length)
                logger.info("[Ollama] Sending POST request to %s", url)

                response = await client.post(url, json=request_payload)

                logger.info("[Ollama] Response status code: %d", response.status_code)
                logger.info("[Ollama] Response headers: %s", dict(response.headers))

                response.raise_for_status()

                result = response.json()
                message = result.get("message", {})
                raw_response = message.get("content", "")
                response_text = raw_response.strip()

                logger.info("[Ollama] Raw response length: %d characters", len(raw_response))
                logger.info("[Ollama] Raw response preview: %s...", raw_response[:300])

                markers_to_remove = [
                    "待校对文本：",
                    "校对后的文本：",
                    "校对后：",
                    "精校后：",
                    "结果：",
                    "校对结果：",
                ]
                for marker in markers_to_remove:
                    if response_text.startswith(marker):
                        response_text = response_text[len(marker):].strip()
                        break
                for marker in markers_to_remove:
                    if marker in response_text:
                        last_idx = response_text.rfind(marker)
                        if last_idx >= 0:
                            before_marker = response_text[:last_idx].strip()
                            after_marker = response_text[last_idx + len(marker):].strip()
                            if len(after_marker) > len(before_marker) * 0.8 or len(before_marker) < 50:
                                response_text = after_marker
                                break

                response_length = len(response_text)

                logger.info("[Ollama] Response received successfully")
                logger.info("[Ollama] Response text length: %d characters", response_length)
                logger.info("[Ollama] Response preview: %s...", response_text[:200])

                if response_length == 0:
                    raise Exception(
                        "Ollama 返回内容为空（可能为模型/服务暂时异常），将触发重试。"
                        " raw_response length=%d" % len(raw_response)
                    )

                if response_length < text_length * 0.5:
                    logger.warning(
                        "[Ollama] Warning: Response length (%d) is much shorter than "
                        "input length (%d). This might indicate truncation or cleaning issue.",
                        response_length,
                        text_length,
                    )
                    logger.warning("[Ollama] Full response: %s", response_text)

                return response_text

        except httpx.TimeoutException as e:
            error_msg = "Ollama API调用超时（%s秒）" % self.timeout
            logger.error("[Ollama] %s", error_msg)
            logger.error("[Ollama] Timeout exception: %s", str(e))
            logger.error("[Ollama] Request URL: %s", url)
            raise Exception(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = "Ollama API连接失败: 无法连接到 %s" % self.base_url
            logger.error("[Ollama] %s", error_msg)
            logger.error("[Ollama] Connection error: %s", str(e))
            logger.error("[Ollama] Request URL: %s", url)
            raise ModelConnectionError(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = "Ollama API返回错误状态码: %s" % e.response.status_code
            logger.error("[Ollama] %s", error_msg)
            logger.error("[Ollama] Response status: %d", e.response.status_code)
            logger.error("[Ollama] Response text: %s", e.response.text[:500])
            logger.error("[Ollama] Request URL: %s", url)
            raise Exception("%s - %s" % (error_msg, e.response.text[:200])) from e
        except Exception as e:
            error_msg = "Ollama API调用失败: %s" % str(e)
            logger.error("[Ollama] %s", error_msg)
            logger.error("[Ollama] Exception type: %s", type(e).__name__)
            logger.error("[Ollama] Exception details: %s", str(e))
            logger.error("[Ollama] Request URL: %s", url)
            raise Exception(error_msg) from e

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
                        logger.info("[Ollama Health] Available models: %s", result.get("models", []))
                    except Exception:
                        pass
                return status_ok
        except Exception as e:
            logger.error("[Ollama Health] Health check failed: %s", str(e))
            logger.error("[Ollama Health] URL: %s", url)
            return False

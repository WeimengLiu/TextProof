"""配置管理模块"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # OpenAI配置
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    
    # DeepSeek配置
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    
    # Ollama配置
    ollama_base_url: str = "http://localhost:11434"
    
    # 默认模型配置
    default_model_provider: str = "openai"
    default_model_name: str = "gpt-4-turbo-preview"
    
    # 文本分段配置
    chunk_size: int = 2000
    chunk_overlap: int = 200
    
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=()  # 解决 model_name 字段冲突警告
    )


settings = Settings()

"""配置管理模块"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, Dict, List


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
    
    # 模型列表配置（用逗号分隔）
    openai_models: str = "gpt-4-turbo-preview,gpt-4,gpt-3.5-turbo,gpt-4o-mini"
    deepseek_models: str = "deepseek-chat,deepseek-coder"
    ollama_models: str = "llama2,llama3,qwen,mistral"
    
    # 文本分段配置
    chunk_size: int = 2000
    chunk_overlap: int = 200
    
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Prompt配置
    prompt_file: Optional[str] = None  # 自定义Prompt文件路径
    
    def _parse_models(self, model_str: str) -> List[str]:
        """解析模型列表字符串"""
        if isinstance(model_str, str):
            return [m.strip() for m in model_str.split(',') if m.strip()]
        return []
    
    def get_models_by_provider(self, provider: str) -> List[str]:
        """根据提供商获取模型列表"""
        model_map = {
            "openai": self.openai_models,
            "deepseek": self.deepseek_models,
            "ollama": self.ollama_models,
        }
        model_str = model_map.get(provider, "")
        return self._parse_models(model_str)
    
    def get_all_models(self) -> Dict[str, List[str]]:
        """获取所有提供商的模型列表"""
        return {
            "openai": self._parse_models(self.openai_models),
            "deepseek": self._parse_models(self.deepseek_models),
            "ollama": self._parse_models(self.ollama_models),
        }
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=()  # 解决 model_name 字段冲突警告
    )


settings = Settings()

"""模型适配器工厂"""
from typing import Dict, Any, Optional
import sys
import os

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models.base import BaseModelAdapter
from models.openai_adapter import OpenAIAdapter
from models.deepseek_adapter import DeepSeekAdapter
from models.ollama_adapter import OllamaAdapter
import config


class ModelAdapterFactory:
    """模型适配器工厂类"""
    
    _adapters: Dict[str, type] = {
        "openai": OpenAIAdapter,
        "deepseek": DeepSeekAdapter,
        "ollama": OllamaAdapter,
    }
    
    @classmethod
    def create_adapter(
        cls, 
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> BaseModelAdapter:
        """
        创建模型适配器
        
        Args:
            provider: 模型提供商（openai/deepseek/ollama）
            model_name: 模型名称
            **kwargs: 其他配置参数
            
        Returns:
            模型适配器实例
        """
        provider = provider or config.settings.default_model_provider
        model_name = model_name or config.settings.default_model_name
        
        if provider not in cls._adapters:
            raise ValueError(f"不支持的模型提供商: {provider}")
        
        adapter_class = cls._adapters[provider]
        
        # 构建配置
        adapter_config = {
            "model_name": model_name,
            **kwargs
        }
        
        # 根据提供商添加特定配置
        if provider == "openai":
            adapter_config["api_key"] = kwargs.get("api_key") or config.settings.openai_api_key
            adapter_config["base_url"] = kwargs.get("base_url") or config.settings.openai_base_url
        elif provider == "deepseek":
            adapter_config["api_key"] = kwargs.get("api_key") or config.settings.deepseek_api_key
            adapter_config["base_url"] = kwargs.get("base_url") or config.settings.deepseek_base_url
        elif provider == "ollama":
            adapter_config["base_url"] = kwargs.get("base_url") or config.settings.ollama_base_url
        
        return adapter_class(adapter_config)
    
    @classmethod
    def get_available_providers(cls) -> list:
        """获取可用的模型提供商列表"""
        return list(cls._adapters.keys())

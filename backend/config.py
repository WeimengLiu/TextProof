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
    
    def update_runtime_config(self, **kwargs):
        """运行时更新配置（仅内存中，重启后恢复）"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def save_to_env_file(self, env_file_path: str = ".env"):
        """保存配置到.env文件"""
        import os
        # 获取backend目录路径
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(backend_dir, env_file_path)
        
        # 读取现有.env文件
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()
        else:
            # 如果文件不存在，从.env.example复制
            example_path = os.path.join(backend_dir, ".env.example")
            if os.path.exists(example_path):
                with open(example_path, "r", encoding="utf-8") as f:
                    env_lines = f.readlines()
        
        # 创建配置映射
        config_map = {
            "CHUNK_SIZE": str(self.chunk_size),
            "CHUNK_OVERLAP": str(self.chunk_overlap),
            "MAX_RETRIES": str(self.max_retries),
            "RETRY_DELAY": str(self.retry_delay),
            "DEFAULT_MODEL_PROVIDER": self.default_model_provider,
            "DEFAULT_MODEL_NAME": self.default_model_name,
            "OPENAI_MODELS": self.openai_models,
            "DEEPSEEK_MODELS": self.deepseek_models,
            "OLLAMA_MODELS": self.ollama_models,
        }
        
        # 更新或添加配置项
        updated_keys = set()
        new_lines = []
        in_config_section = False
        
        for line in env_lines:
            stripped = line.strip()
            
            # 保留注释和空行
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                # 检查是否进入配置区域
                if "配置" in stripped or "Config" in stripped:
                    in_config_section = True
                continue
            
            # 解析配置行
            if "=" in stripped:
                key = stripped.split("=")[0].strip()
                if key in config_map:
                    # 更新配置值，保留原有格式（如果有引号等）
                    original_line = line.rstrip()
                    if "=" in original_line:
                        # 保留等号前的部分和格式
                        prefix = original_line.split("=")[0]
                        new_lines.append(f"{prefix}={config_map[key]}\n")
                    else:
                        new_lines.append(f"{key}={config_map[key]}\n")
                    updated_keys.add(key)
                    continue
            
            # 保留其他行
            new_lines.append(line)
        
        # 添加未存在的配置项（在适当位置）
        missing_keys = set(config_map.keys()) - updated_keys
        if missing_keys:
            # 在文件末尾添加新配置项
            new_lines.append("\n# 自动添加的配置项\n")
            for key in sorted(missing_keys):
                new_lines.append(f"{key}={config_map[key]}\n")
        
        # 写入文件
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return True
        except Exception as e:
            print(f"保存.env文件失败: {e}")
            return False
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=()  # 解决 model_name 字段冲突警告
    )


settings = Settings()

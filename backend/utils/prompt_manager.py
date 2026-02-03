"""Prompt管理模块"""
from typing import Optional
import os


class PromptManager:
    """Prompt管理器"""
    
    DEFAULT_PROMPT = """你是一名专业的文本校对员。你的任务是纠正文本中的错误，但必须严格遵守以下规则：

【核心原则】
1. 只纠正错误，不改变原文意思和风格
2. 只修正：错别字、病句、拼音或谐音转简体中文、明显错误的标点符号
3. 禁止任何文风、语气、措辞层面的优化
4. 禁止添加、删除或改写内容
5. 如果原文没有明显错误，必须保持完全不变

【严格禁止的行为】
- ❌ 禁止同义词替换（如"巴掌"改为"耳光"、"说"改为"道"、"走"改为"行"等）
- ❌ 禁止用词优化（如"好"改为"优秀"、"大"改为"巨大"等）
- ❌ 禁止语气调整（如"不行"改为"不可以"、"快点"改为"请尽快"等）
- ❌ 禁止风格转换（如口语改书面语、方言改普通话等）
- ❌ 禁止任何形式的"润色"、"优化"、"改进"表达

【具体规则】
- 错别字：将错误的字词替换为正确的（如"的"误用为"地"、"在"误用为"再"）
- 病句：修正语法错误，但保持原意不变（如"我去了学校昨天"改为"我昨天去了学校"）
- 拼音转中文：将拼音或谐音字转换为正确的简体中文（如"ni hao"改为"你好"）
- 标点错误：修正明显错误的标点符号（如句号误用为逗号、缺少引号等）
- 保持原意：任何修改都不能改变原文要表达的意思
- 保持风格：保持原文的语言风格和表达方式，包括用词习惯

【重要提醒】
- "巴掌"和"耳光"意思相近，但这是同义词替换，必须禁止
- "说"和"道"、"走"和"行"、"看"和"瞧"等都属于同义词，不能替换
- 只有真正的错别字（如"在"写成"再"、"的"写成"地"）才能修改
- 如果原文用词正确，即使有其他"更好"的表达方式，也必须保持原样

【输出要求】
直接输出校对后的文本，不要添加任何说明、注释或标记。如果原文没有错误，直接原样输出。

现在请校对以下文本："""
    
    def __init__(self, prompt_file: Optional[str] = None):
        """
        初始化Prompt管理器
        
        Args:
            prompt_file: 自定义prompt文件路径（可选，优先使用环境变量配置）
        """
        # 延迟导入config避免循环导入
        try:
            import config as config_module
            env_prompt_file = getattr(config_module.settings, 'prompt_file', None) if hasattr(config_module, 'settings') else None
            env_ollama_prompt_file = getattr(config_module.settings, 'ollama_prompt_file', None) if hasattr(config_module, 'settings') else None
        except Exception:
            env_prompt_file = None
            env_ollama_prompt_file = None
        
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        raw_path = prompt_file or env_prompt_file
        if raw_path:
            if os.path.isabs(raw_path):
                self.prompt_file_path = raw_path
            else:
                self.prompt_file_path = os.path.join(backend_dir, raw_path.lstrip('./'))
        else:
            self.prompt_file_path = None
        
        raw_ollama_path = env_ollama_prompt_file
        if raw_ollama_path:
            if os.path.isabs(raw_ollama_path):
                self.ollama_prompt_file_path = raw_ollama_path
            else:
                self.ollama_prompt_file_path = os.path.join(backend_dir, raw_ollama_path.lstrip('./'))
        else:
            self.ollama_prompt_file_path = None
        # 默认 Ollama 文件路径（保存时写入此处；未配置 OLLAMA_PROMPT_FILE 时也从此加载，避免刷新被还原）
        self.ollama_default_file_path = os.path.join(backend_dir, "prompts", "ollama_custom_prompt.txt")
        
        self.prompt = self.DEFAULT_PROMPT
        self.ollama_prompt = self.DEFAULT_PROMPT
        self._load_prompt_from_file()
    
    def _load_prompt_from_file(self) -> None:
        """从文件加载云端与 Ollama 两套 prompt。先加载云端，再加载 Ollama（无独立文件则与云端相同）。"""
        if self.prompt_file_path and os.path.exists(self.prompt_file_path):
            try:
                with open(self.prompt_file_path, "r", encoding="utf-8") as f:
                    self.prompt = f.read().strip()
            except Exception as e:
                print("警告: 无法读取Prompt文件 %s: %s，使用默认Prompt" % (self.prompt_file_path, e))
                self.prompt = self.DEFAULT_PROMPT
        else:
            if self.prompt_file_path:
                print("提示: Prompt文件不存在 %s，使用默认Prompt" % self.prompt_file_path)
            self.prompt = self.DEFAULT_PROMPT
        
        ollama_path = self.ollama_prompt_file_path or self.ollama_default_file_path
        if ollama_path and os.path.exists(ollama_path):
            try:
                with open(ollama_path, "r", encoding="utf-8") as f:
                    self.ollama_prompt = f.read().strip()
            except Exception as e:
                print("警告: 无法读取 Ollama Prompt 文件 %s: %s，使用云端 Prompt" % (ollama_path, e))
                self.ollama_prompt = self.prompt
        else:
            if self.ollama_prompt_file_path:
                print("提示: Ollama Prompt 文件不存在 %s，使用云端 Prompt" % self.ollama_prompt_file_path)
            self.ollama_prompt = self.prompt
    
    def get_prompt(self, provider: Optional[str] = None, reload: bool = False) -> str:
        """
        获取当前使用的 prompt。
        
        Args:
            provider: 模型提供商，'ollama' 返回 Ollama 专用 prompt，否则返回云端 prompt。
            reload: 是否重新从文件加载（默认 False，使用缓存）
        
        Returns:
            prompt 文本
        """
        if reload:
            self._load_prompt_from_file()
        if provider and str(provider).lower() == "ollama":
            return self.ollama_prompt
        return self.prompt
    
    def set_prompt(self, prompt: str, provider: Optional[str] = None) -> None:
        """设置新的 prompt。provider=='ollama' 时设置 Ollama 专用，否则设置云端。"""
        if provider and str(provider).lower() == "ollama":
            self.ollama_prompt = prompt
        else:
            self.prompt = prompt
    
    def save_prompt(self, file_path: str, provider: Optional[str] = None) -> None:
        """保存 prompt 到指定文件。provider=='ollama' 时保存 Ollama 专用内容，否则保存云端。"""
        content = self.ollama_prompt if (provider and str(provider).lower() == "ollama") else self.prompt
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def save_prompt_to_default_file(self, provider: Optional[str] = None) -> str:
        """
        保存 Prompt 到默认文件。
        provider is None 时保存云端到 prompts/custom_prompt.txt；
        provider=='ollama' 时保存 Ollama 到 prompts/ollama_custom_prompt.txt。
        
        Returns:
            保存的文件路径
        """
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompts_dir = os.path.join(backend_dir, "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        if provider and str(provider).lower() == "ollama":
            default_file = os.path.join(prompts_dir, "ollama_custom_prompt.txt")
            with open(default_file, "w", encoding="utf-8") as f:
                f.write(self.ollama_prompt)
        else:
            default_file = os.path.join(prompts_dir, "custom_prompt.txt")
            with open(default_file, "w", encoding="utf-8") as f:
                f.write(self.prompt)
        return default_file


# 全局prompt管理器实例
prompt_manager = PromptManager()

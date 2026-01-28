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
        except:
            env_prompt_file = None
        
        raw_path = prompt_file or env_prompt_file
        # 解析路径：如果是相对路径，相对于 backend 目录
        if raw_path:
            if os.path.isabs(raw_path):
                self.prompt_file_path = raw_path
            else:
                # 获取 backend 目录（utils 目录的父目录）
                backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                self.prompt_file_path = os.path.join(backend_dir, raw_path.lstrip('./'))
        else:
            self.prompt_file_path = None
        
        self.prompt = self.DEFAULT_PROMPT
        self._load_prompt_from_file()
    
    def _load_prompt_from_file(self) -> None:
        """从文件加载prompt（如果文件存在）"""
        if self.prompt_file_path and os.path.exists(self.prompt_file_path):
            try:
                with open(self.prompt_file_path, "r", encoding="utf-8") as f:
                    self.prompt = f.read().strip()
            except Exception as e:
                print(f"警告: 无法读取Prompt文件 {self.prompt_file_path}: {e}，使用默认Prompt")
                self.prompt = self.DEFAULT_PROMPT
        else:
            if self.prompt_file_path:
                print(f"提示: Prompt文件不存在 {self.prompt_file_path}，使用默认Prompt")
            self.prompt = self.DEFAULT_PROMPT
    
    def get_prompt(self, reload: bool = False) -> str:
        """
        获取当前使用的prompt
        
        Args:
            reload: 是否重新从文件加载（默认False，使用缓存）
        
        Returns:
            prompt文本
        """
        if reload:
            self._load_prompt_from_file()
        return self.prompt
    
    def set_prompt(self, prompt: str):
        """设置新的prompt"""
        self.prompt = prompt
    
    def save_prompt(self, file_path: str):
        """保存prompt到文件"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.prompt)
    
    def save_prompt_to_default_file(self) -> str:
        """
        保存Prompt到默认文件（prompts/custom_prompt.txt）
        
        Returns:
            保存的文件路径
        """
        # 获取backend目录路径（utils 目录的父目录）
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompts_dir = os.path.join(backend_dir, "prompts")
        
        # 确保prompts目录存在
        os.makedirs(prompts_dir, exist_ok=True)
        
        # 保存到默认文件
        default_file = os.path.join(prompts_dir, "custom_prompt.txt")
        with open(default_file, "w", encoding="utf-8") as f:
            f.write(self.prompt)
        
        return default_file


# 全局prompt管理器实例
prompt_manager = PromptManager()

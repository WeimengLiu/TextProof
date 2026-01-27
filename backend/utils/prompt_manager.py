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

【具体规则】
- 错别字：将错误的字词替换为正确的（如"的"误用为"地"）
- 病句：修正语法错误，但保持原意不变
- 拼音转中文：将拼音或谐音字转换为正确的简体中文
- 标点错误：修正明显错误的标点符号（如句号误用为逗号）
- 保持原意：任何修改都不能改变原文要表达的意思
- 保持风格：保持原文的语言风格和表达方式

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
        
        file_path = prompt_file or env_prompt_file
        
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.prompt = f.read().strip()
            except Exception as e:
                print(f"警告: 无法读取Prompt文件 {file_path}: {e}，使用默认Prompt")
                self.prompt = self.DEFAULT_PROMPT
        else:
            self.prompt = self.DEFAULT_PROMPT
    
    def get_prompt(self) -> str:
        """获取当前使用的prompt"""
        return self.prompt
    
    def set_prompt(self, prompt: str):
        """设置新的prompt"""
        self.prompt = prompt
    
    def save_prompt(self, file_path: str):
        """保存prompt到文件"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.prompt)


# 全局prompt管理器实例
prompt_manager = PromptManager()

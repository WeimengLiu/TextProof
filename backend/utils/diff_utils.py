"""文本差异对比工具"""
try:
    from diff_match_patch import diff_match_patch
except ImportError:
    # 如果导入失败，使用备用实现
    class diff_match_patch:
        def diff_main(self, text1, text2):
            # 简单实现：如果相同返回相同标记，否则返回差异
            if text1 == text2:
                return [(0, text1)]
            return [(-1, text1), (1, text2)]
        
        def diff_cleanupSemantic(self, diffs):
            pass

from typing import List, Tuple


def compute_diff(original: str, corrected: str) -> List[Tuple[int, str]]:
    """
    计算两个文本的差异
    
    Args:
        original: 原文
        corrected: 校对后的文本
        
    Returns:
        差异列表，每个元素为 (操作类型, 文本片段)
        操作类型：-1=删除, 0=相同, 1=添加
    """
    dmp = diff_match_patch()
    diffs = dmp.diff_main(original, corrected)
    dmp.diff_cleanupSemantic(diffs)
    return diffs


def normalize_text_for_comparison(text: str) -> str:
    """
    标准化文本用于比较（忽略纯格式差异）
    
    Args:
        text: 待标准化的文本
        
    Returns:
        标准化后的文本
    """
    # 将多个连续空格替换为单个空格
    import re
    text = re.sub(r' +', ' ', text)
    # 将多个连续换行替换为单个换行
    text = re.sub(r'\n\s*\n+', '\n', text)
    # 去除首尾空白
    text = text.strip()
    return text


def has_meaningful_changes(original: str, corrected: str) -> bool:
    """
    判断两个文本是否有有意义的差异（忽略纯格式差异）
    
    Args:
        original: 原文
        corrected: 校对后的文本
        
    Returns:
        如果有有意义的差异返回True，否则返回False
    """
    # 如果完全相同，肯定没有变化
    if original == corrected:
        return False
    
    # 标准化后比较
    normalized_original = normalize_text_for_comparison(original)
    normalized_corrected = normalize_text_for_comparison(corrected)
    
    if normalized_original == normalized_corrected:
        return False
    
    # 使用diff算法检查是否有非空白字符的差异
    diffs = compute_diff(original, corrected)
    for op, text in diffs:
        if op != 0 and text.strip():  # 有非空白字符的差异
            return True
    
    return False


def highlight_diff(original: str, corrected: str) -> dict:
    """
    生成高亮差异数据
    
    Args:
        original: 原文
        corrected: 校对后的文本
        
    Returns:
        包含差异信息的字典
    """
    diffs = compute_diff(original, corrected)
    
    original_segments = []
    corrected_segments = []
    
    # 统计有意义的差异（排除纯空白字符差异）
    has_meaningful_changes = False
    
    for op, text in diffs:
        if op == 0:  # 相同部分
            original_segments.append({"text": text, "type": "same"})
            corrected_segments.append({"text": text, "type": "same"})
        elif op == -1:  # 删除（原文有，校对后删除）
            # 检查是否是纯空白字符
            if text.strip():  # 有非空白字符，才认为是有意义的差异
                has_meaningful_changes = True
            original_segments.append({"text": text, "type": "deleted"})
        elif op == 1:  # 添加（校对后新增）
            # 检查是否是纯空白字符
            if text.strip():  # 有非空白字符，才认为是有意义的差异
                has_meaningful_changes = True
            corrected_segments.append({"text": text, "type": "added"})
    
    # 如果只有空白字符差异，也检查标准化后的文本是否相同
    if not has_meaningful_changes:
        normalized_original = normalize_text_for_comparison(original)
        normalized_corrected = normalize_text_for_comparison(corrected)
        if normalized_original == normalized_corrected:
            has_meaningful_changes = False
    
    return {
        "original_segments": original_segments,
        "corrected_segments": corrected_segments,
        "has_changes": has_meaningful_changes
    }

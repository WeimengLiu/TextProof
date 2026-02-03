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


def has_meaningful_changes(original: str, corrected: str) -> bool:
    """
    判断两个文本是否有差异（比对时忽略首尾空格，仅比较 strip 后的内容）
    
    Args:
        original: 原文
        corrected: 校对后的文本
        
    Returns:
        若 strip 后仍有差异返回 True，仅首尾空格不同则返回 False
    """
    return original.strip() != corrected.strip()


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
    # 比对时忽略首尾空格：仅当 strip 后不同才算有变化
    has_meaningful = original.strip() != corrected.strip()
    
    for op, text in diffs:
        if op == 0:  # 相同部分
            original_segments.append({"text": text, "type": "same"})
            corrected_segments.append({"text": text, "type": "same"})
        elif op == -1:  # 删除（原文有，校对后删除）
            original_segments.append({"text": text, "type": "deleted"})
        elif op == 1:  # 添加（校对后新增）
            corrected_segments.append({"text": text, "type": "added"})
    
    return {
        "original_segments": original_segments,
        "corrected_segments": corrected_segments,
        "has_changes": has_meaningful
    }

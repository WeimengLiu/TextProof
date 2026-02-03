"""文本分段工具"""
from typing import List
import sys
import os
import logging

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

logger = logging.getLogger(__name__)


class TextSplitter:
    """文本分段器"""
    
    def __init__(
        self, 
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.chunk_size = chunk_size or config.settings.chunk_size
        self.chunk_overlap = chunk_overlap or config.settings.chunk_overlap
        
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap必须小于chunk_size")
    
    def split(self, text: str) -> List[str]:
        """
        将文本分割成多个片段
        
        Args:
            text: 待分割的文本
            
        Returns:
            文本片段列表
        """
        if not text:
            return []
        
        # 按段落分割（保留段落结构）
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # 如果当前段落本身就很长，需要进一步分割
            if len(para) > self.chunk_size:
                # 先保存当前chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())  # 去首尾空白以减少 token
                    current_chunk = ""
                
                # 分割长段落
                para_chunks = self._split_long_paragraph(para)
                chunks.extend(para_chunks)
            else:
                # 检查添加当前段落后是否超过chunk_size
                test_chunk = current_chunk + "\n\n" + para if current_chunk else para
                
                if len(test_chunk) <= self.chunk_size:
                    current_chunk = test_chunk
                else:
                    # 保存当前chunk，开始新chunk
                    if current_chunk:
                        chunks.append(current_chunk.strip())  # 去首尾空白以减少 token
                    
                    # 如果有overlap，从上一chunk末尾取部分内容
                    if chunks and self.chunk_overlap > 0:
                        overlap_text = self._get_overlap_text(chunks[-1], self.chunk_overlap)
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
        
        # 添加最后一个chunk（去首尾空白以减少 token）
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_long_paragraph(self, para: str) -> List[str]:
        """分割超长段落"""
        chunks = []
        sentences = para.split("。")
        
        current_chunk = ""
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()  # 去首尾空白以减少 token
            if not sentence:
                continue
            
            # 添加句号（除了最后一句）
            if i < len(sentences) - 1:
                sentence += "。"
            
            test_chunk = current_chunk + sentence if current_chunk else sentence
            
            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 处理overlap
                if chunks and self.chunk_overlap > 0:
                    overlap_text = self._get_overlap_text(chunks[-1], self.chunk_overlap)
                    current_chunk = overlap_text + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """获取文本末尾的overlap部分"""
        if len(text) <= overlap_size:
            return text
        
        # 从末尾开始，尽量在句号或换行处截断
        overlap_text = text[-overlap_size:]
        
        # 尝试在句号处截断
        period_idx = overlap_text.find("。")
        if period_idx > overlap_size * 0.3:  # 如果句号位置合理
            return overlap_text[period_idx + 1:]
        
        # 尝试在换行处截断
        newline_idx = overlap_text.find("\n")
        if newline_idx > overlap_size * 0.3:
            return overlap_text[newline_idx + 1:]
        
        return overlap_text
    
    def merge(self, chunks: List[str]) -> str:
        """
        合并文本片段，智能去除重复的overlap部分
        
        Args:
            chunks: 文本片段列表
            
        Returns:
            合并后的完整文本
        """
        if not chunks:
            return ""
        
        if len(chunks) == 1:
            return chunks[0]
        
        merged = chunks[0]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            
            # 尝试找到重叠部分并去除
            overlap_removed = self._remove_overlap(prev_chunk, curr_chunk)
            
            if overlap_removed is not None:
                # 找到了重叠，只添加不重叠的部分
                removed_len = len(curr_chunk) - len(overlap_removed)
                logger.debug("[TextSplitter] Chunk %d: Found overlap of %d chars, removed", i+1, removed_len)
                merged += overlap_removed
            else:
                # 没找到重叠，直接拼接（用换行分隔）
                logger.debug("[TextSplitter] Chunk %d: No overlap found, appending full chunk", i+1)
                merged += "\n\n" + curr_chunk
        
        return merged
    
    def _remove_overlap(self, prev_chunk: str, curr_chunk: str) -> str:
        """
        尝试找到并移除两个chunk之间的重叠部分
        
        Returns:
            如果找到重叠，返回curr_chunk去除重叠后的部分
            如果没找到重叠，返回None
        """
        if not prev_chunk or not curr_chunk:
            return None
        
        # 计算最大可能的overlap长度（考虑chunk_overlap配置，但允许一些灵活性）
        max_overlap = min(
            len(prev_chunk),
            len(curr_chunk),
            self.chunk_overlap * 3  # 允许最多3倍的overlap，因为模型可能修改了文本
        )
        
        # 策略1: 完全匹配（最理想的情况）
        for overlap_len in range(max_overlap, max(0, self.chunk_overlap - 50), -1):
            prev_suffix = prev_chunk[-overlap_len:]
            curr_prefix = curr_chunk[:overlap_len]
            
            if prev_suffix == curr_prefix:
                return curr_chunk[overlap_len:]
        
        # 策略2: 在句号处匹配（更宽松的匹配）
        # 查找prev_chunk末尾的最后一个句号
        period_idx = prev_chunk.rfind("。")
        if period_idx >= len(prev_chunk) - max_overlap:
            # 句号在overlap范围内
            matched_suffix = prev_chunk[period_idx + 1:].strip()
            if matched_suffix and curr_chunk.startswith(matched_suffix):
                return curr_chunk[len(matched_suffix):]
            # 也尝试匹配句号后的部分（去除空格）
            matched_suffix_no_space = matched_suffix.replace(" ", "").replace("\n", "")
            curr_prefix_no_space = curr_chunk[:len(matched_suffix)].replace(" ", "").replace("\n", "")
            if matched_suffix_no_space and curr_prefix_no_space.startswith(matched_suffix_no_space):
                return curr_chunk[len(matched_suffix):]
        
        # 策略3: 在换行处匹配
        newline_idx = prev_chunk.rfind("\n")
        if newline_idx >= len(prev_chunk) - max_overlap:
            matched_suffix = prev_chunk[newline_idx + 1:].strip()
            if matched_suffix and curr_chunk.startswith(matched_suffix):
                return curr_chunk[len(matched_suffix):]
        
        # 策略4: 查找curr_chunk开头在prev_chunk末尾的最长匹配
        # 这样可以处理模型修改了文本但保留了部分内容的情况
        best_match_len = 0
        search_len = min(200, len(curr_chunk), len(prev_chunk))  # 最多检查200个字符
        for test_len in range(search_len, 10, -1):  # 至少匹配10个字符
            test_prefix = curr_chunk[:test_len]
            if prev_chunk.endswith(test_prefix):
                best_match_len = test_len
                break
        
        if best_match_len >= 10:  # 至少匹配10个字符才认为是有效的overlap
            return curr_chunk[best_match_len:]
        
        # 策略5: 如果prev_chunk和curr_chunk都很短，且curr_chunk完全包含在prev_chunk中
        # 这种情况可能是模型返回了重复的内容
        if len(curr_chunk) < len(prev_chunk) * 0.5:
            if curr_chunk in prev_chunk:
                # curr_chunk完全包含在prev_chunk中，可能是重复，返回空
                return ""
        
        # 如果还是找不到，返回None，让调用者直接拼接
        return None

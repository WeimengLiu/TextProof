"""文本分段工具"""
from typing import List
import sys
import os

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config


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
                    chunks.append(current_chunk.strip())
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
                        chunks.append(current_chunk.strip())
                    
                    # 如果有overlap，从上一chunk末尾取部分内容
                    if chunks and self.chunk_overlap > 0:
                        overlap_text = self._get_overlap_text(chunks[-1], self.chunk_overlap)
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
        
        # 添加最后一个chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_long_paragraph(self, para: str) -> List[str]:
        """分割超长段落"""
        chunks = []
        sentences = para.split("。")
        
        current_chunk = ""
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
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
        合并文本片段
        
        Args:
            chunks: 文本片段列表
            
        Returns:
            合并后的完整文本
        """
        if not chunks:
            return ""
        
        # 简单合并，去除重复的overlap部分
        merged = chunks[0]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            
            # 检查是否有overlap
            overlap_len = min(len(prev_chunk), len(curr_chunk), self.chunk_overlap)
            if overlap_len > 0:
                prev_suffix = prev_chunk[-overlap_len:]
                curr_prefix = curr_chunk[:overlap_len]
                
                # 如果发现重复，跳过overlap部分
                if prev_suffix == curr_prefix:
                    merged += curr_chunk[overlap_len:]
                else:
                    # 尝试在句号处匹配
                    period_idx = prev_suffix.rfind("。")
                    if period_idx > 0:
                        matched = prev_suffix[period_idx + 1:]
                        if curr_chunk.startswith(matched):
                            merged += curr_chunk[len(matched):]
                        else:
                            merged += "\n\n" + curr_chunk
                    else:
                        merged += "\n\n" + curr_chunk
            else:
                merged += "\n\n" + curr_chunk
        
        return merged

"""章节切割工具"""
import re
from typing import List, Dict


class ChapterSplitter:
    """章节切割器"""
    
    # 常见的章节标题模式
    CHAPTER_PATTERNS = [
        # 带【】的章节标题（如：【第一卷 少年热血】 第1章）
        r'^【[^】]+】\s*第[一二三四五六七八九十百千万\d]+章[^\n]*',
        # 第X章、第X节（不带卷）
        r'^第[一二三四五六七八九十百千万\d]+章[^\n]*',
        r'^第[一二三四五六七八九十百千万\d]+节[^\n]*',
        # Chapter X、ChapterX
        r'^[Cc]hapter\s*\d+[^\n]*',
        r'^[Cc]h\.\s*\d+[^\n]*',
        # 数字开头（如：1. 第一章标题）
        r'^\d+[\.、]\s*[^\n]*',
        # 中文数字开头（如：一、第一章标题）
        r'^[一二三四五六七八九十]+[\.、]\s*[^\n]*',
        # 特殊标记（如：*** 第一章 ***）
        r'^[*\-_=]{3,}\s*[^\n]*',
        # 卷、部、篇
        r'^第[一二三四五六七八九十百千万\d]+[卷部篇][^\n]*',
    ]
    
    def __init__(self):
        """初始化章节切割器"""
        # 编译所有正则表达式
        self.patterns = [re.compile(pattern, re.MULTILINE) for pattern in self.CHAPTER_PATTERNS]
    
    def split_by_chapters(self, text: str) -> List[Dict[str, any]]:
        """
        按章节切割文本
        
        Args:
            text: 待切割的文本
            
        Returns:
            章节列表，每个章节包含：
            - chapter_index: 章节索引（从1开始）
            - chapter_title: 章节标题
            - chapter_content: 章节内容
            - start_pos: 在原文本中的起始位置
            - end_pos: 在原文本中的结束位置
        """
        if not text:
            return []
        
        chapters = []
        lines = text.split('\n')
        current_chapter = None
        current_content = []
        chapter_index = 0
        
        # 跳过文件开头的非章节内容（分隔线、作者信息、简介等）
        skip_prefix = True
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 检查是否是章节标题
            is_chapter_title = False
            chapter_title = None
            
            if line:  # 非空行
                # 过滤掉分隔线（全是特殊字符）
                if re.match(r'^[=\-*_]{10,}$', line):
                    i += 1
                    continue
                
                # 过滤掉纯数字或纯符号行
                if re.match(r'^[\d\s\.\-]+$', line) and len(line) < 20:
                    i += 1
                    continue
                
                # 过滤掉明显的文件头信息（包含"作者"、"简介"等）
                if i < 20:  # 只在文件前20行检查
                    if any(keyword in line for keyword in ['作者', '简介', '内容简介', '目录', '序言', '前言']):
                        i += 1
                        continue
                
                for pattern in self.patterns:
                    match = pattern.match(line)
                    if match:
                        is_chapter_title = True
                        chapter_title = line
                        break
                
                # 额外检查：如果行很短（少于50字符）且包含"章"、"节"等关键词
                if not is_chapter_title and len(line) < 50:
                    if any(keyword in line for keyword in ['章', '节', 'Chapter', 'chapter', 'Ch.', 'ch.']):
                        # 检查是否包含数字或中文数字，且不是纯正文
                        if re.search(r'[第\d一二三四五六七八九十]', line):
                            # 排除明显是正文的情况（包含太多标点或普通文字）
                            if not re.search(r'[，。！？；：、]', line) or line.count('【') > 0:
                                is_chapter_title = True
                                chapter_title = line
            
            if is_chapter_title:
                # 如果还在跳过前缀阶段，且这是第一个真正的章节标题，停止跳过
                if skip_prefix and chapter_index == 0:
                    # 检查是否是真正的章节标题（包含"第X章"或"Chapter"等）
                    if re.search(r'第[一二三四五六七八九十百千万\d]+章', chapter_title) or \
                       re.search(r'Chapter\s*\d+', chapter_title, re.IGNORECASE) or \
                       chapter_title.count('【') > 0:
                        skip_prefix = False
                        # 丢弃之前收集的内容（前缀内容）
                        current_content = []
                    else:
                        # 不是真正的章节标题，继续跳过
                        i += 1
                        continue
                
                # 保存上一章节
                if current_chapter is not None:
                    chapter_content = '\n'.join(current_content).strip()
                    if chapter_content:
                        chapters.append({
                            'chapter_index': current_chapter['chapter_index'],
                            'chapter_title': current_chapter['chapter_title'],
                            'chapter_content': chapter_content,
                            'start_pos': current_chapter['start_pos'],
                            'end_pos': current_chapter['start_pos'] + len(chapter_content),
                        })
                
                # 开始新章节
                chapter_index += 1
                start_pos = sum(len(lines[j]) + 1 for j in range(i))  # +1 for newline
                current_chapter = {
                    'chapter_index': chapter_index,
                    'chapter_title': chapter_title,
                    'start_pos': start_pos,
                }
                current_content = []
                i += 1
                
                # 跳过章节标题后的空行
                while i < len(lines) and not lines[i].strip():
                    i += 1
            else:
                # 如果还在跳过前缀阶段，跳过这些行
                if skip_prefix:
                    i += 1
                    continue
                
                # 添加到当前章节内容
                if current_chapter is None:
                    # 如果没有找到章节标题，创建一个默认章节
                    chapter_index += 1
                    start_pos = sum(len(lines[j]) + 1 for j in range(i))
                    current_chapter = {
                        'chapter_index': chapter_index,
                        'chapter_title': f'第{chapter_index}章',
                        'start_pos': start_pos,
                    }
                
                current_content.append(lines[i])
                i += 1
        
        # 保存最后一个章节
        if current_chapter is not None:
            chapter_content = '\n'.join(current_content).strip()
            if chapter_content:
                chapters.append({
                    'chapter_index': current_chapter['chapter_index'],
                    'chapter_title': current_chapter['chapter_title'],
                    'chapter_content': chapter_content,
                    'start_pos': current_chapter['start_pos'],
                    'end_pos': current_chapter['start_pos'] + len(chapter_content),
                })
        
        # 如果没有检测到章节，将整个文本作为一章
        if not chapters:
            chapters.append({
                'chapter_index': 1,
                'chapter_title': '全文',
                'chapter_content': text,
                'start_pos': 0,
                'end_pos': len(text),
            })
        
        return chapters
    
    def detect_chapters(self, text: str) -> Dict[str, any]:
        """
        检测文本中的章节信息（不切割）
        
        Args:
            text: 待检测的文本
            
        Returns:
            章节信息字典，包含：
            - has_chapters: 是否检测到章节
            - chapter_count: 章节数量
            - chapters: 章节标题列表
        """
        chapters = self.split_by_chapters(text)
        
        return {
            'has_chapters': len(chapters) > 1,
            'chapter_count': len(chapters),
            'chapters': [
                {
                    'index': ch['chapter_index'],
                    'title': ch['chapter_title'],
                    'length': len(ch['chapter_content']),
                }
                for ch in chapters
            ],
        }

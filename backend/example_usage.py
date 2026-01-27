"""使用示例：直接调用校对服务"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.correction_service import CorrectionService


async def main():
    """示例：校对文本"""
    
    # 创建校对服务
    service = CorrectionService(
        provider="openai",  # 或 "deepseek", "ollama"
        model_name="gpt-4-turbo-preview"
    )
    
    # 待校对的文本
    text = """
    这是一段需要校对的文本。里面可能有错别字，比如"的"和"地"的误用。
    也可能有病句，比如语法错误。
    还有拼音转中文的情况，比如"ni hao"应该转换为"你好"。
    标点符号也可能有错误，比如句号误用为逗号。
    """
    
    # 定义进度回调
    def progress_callback(current, total):
        print(f"进度: {current}/{total} ({current*100//total}%)")
    
    # 执行校对
    print("开始校对...")
    result = await service.correct_text(text, progress_callback=progress_callback)
    
    # 输出结果
    print("\n原文:")
    print(result["original"])
    print("\n校对后:")
    print(result["corrected"])
    print(f"\n处理了 {result['chunks_processed']} 个片段，共 {result['total_chunks']} 个片段")
    print(f"是否有变化: {result['original'] != result['corrected']}")


if __name__ == "__main__":
    asyncio.run(main())

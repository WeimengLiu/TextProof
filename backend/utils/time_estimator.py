"""处理时间估算工具"""
import math


def estimate_processing_time(file_size_bytes: int, chunk_size: int = 2000, chunk_overlap: int = 200) -> dict:
    """
    估算处理时间
    
    Args:
        file_size_bytes: 文件大小（字节）
        chunk_size: 分段大小（字符数）
        chunk_overlap: 分段重叠大小（字符数）
        
    Returns:
        包含估算信息的字典
    """
    # 估算字符数（假设UTF-8编码，中文字符占3字节，英文占1字节，取平均值2.5字节/字符）
    estimated_chars = int(file_size_bytes / 2.5)
    
    # 计算分段数（考虑overlap）
    effective_chunk_size = chunk_size - chunk_overlap
    estimated_chunks = math.ceil(estimated_chars / effective_chunk_size)
    
    # 不同模型的平均处理时间（秒/段）
    model_times = {
        "gpt-4-turbo-preview": 5.0,      # GPT-4: 3-8秒，平均5秒
        "gpt-4": 5.5,                     # GPT-4: 4-8秒，平均5.5秒
        "gpt-3.5-turbo": 2.0,             # GPT-3.5: 1-3秒，平均2秒
        "gpt-4o-mini": 1.5,               # GPT-4o-mini: 1-2秒，平均1.5秒
        "deepseek-chat": 3.0,             # DeepSeek: 2-5秒，平均3秒
        "deepseek-coder": 3.5,            # DeepSeek Coder: 2-5秒，平均3.5秒
        "ollama-llama": 10.0,             # Ollama本地: 5-15秒，平均10秒
        "default": 4.0,                   # 默认估算
    }
    
    results = {}
    for model_name, time_per_chunk in model_times.items():
        total_seconds = estimated_chunks * time_per_chunk
        total_minutes = total_seconds / 60
        total_hours = total_minutes / 60
        
        results[model_name] = {
            "estimated_chars": estimated_chars,
            "estimated_chunks": estimated_chunks,
            "time_per_chunk_seconds": time_per_chunk,
            "total_seconds": total_seconds,
            "total_minutes": round(total_minutes, 1),
            "total_hours": round(total_hours, 2),
            "formatted_time": format_time(total_seconds),
        }
    
    return results


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{int(minutes)}分钟{int(seconds % 60)}秒"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        secs = int(seconds % 60)
        if minutes == 0 and secs == 0:
            return f"{hours}小时"
        elif secs == 0:
            return f"{hours}小时{minutes}分钟"
        else:
            return f"{hours}小时{minutes}分钟{secs}秒"


if __name__ == "__main__":
    # 测试：2MB文件
    file_size = 2 * 1024 * 1024  # 2MB
    results = estimate_processing_time(file_size)
    
    print(f"文件大小: {file_size / (1024*1024):.2f} MB")
    print(f"估算字符数: {results['default']['estimated_chars']:,}")
    print(f"估算分段数: {results['default']['estimated_chunks']}")
    print("\n不同模型的估算时间:")
    print("-" * 60)
    for model, info in results.items():
        if model != "default":
            print(f"{model:25s} | {info['formatted_time']:15s} | {info['total_minutes']:6.1f}分钟")

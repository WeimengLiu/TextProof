"""DeepSeek API费用估算工具"""
import math


# DeepSeek定价（每百万token，美元）
DEEPSEEK_PRICING = {
    "deepseek-chat": {
        "input_cache_hit": 0.028,      # $0.028/M tokens (缓存命中)
        "input_cache_miss": 0.28,      # $0.28/M tokens (缓存未命中)
        "output": 0.42,                # $0.42/M tokens
    },
    "deepseek-coder": {
        "input_cache_hit": 0.028,
        "input_cache_miss": 0.28,
        "output": 0.42,
    },
}

# 默认Prompt长度（估算token数）
DEFAULT_PROMPT_TOKENS = 250  # 约250个token

# 字符到token的转换率（中文为主）
# 中文字符: 1字符 ≈ 1.5 tokens
# 英文单词: 1单词 ≈ 1.3 tokens
# 混合文本（中文为主）: 1字符 ≈ 1.4-1.6 tokens
CHARS_TO_TOKENS_RATIO = 1.5  # 保守估算


def estimate_tokens(file_size_bytes: int, chunk_size: int = 2000, chunk_overlap: int = 200) -> dict:
    """
    估算token消耗
    
    Args:
        file_size_bytes: 文件大小（字节）
        chunk_size: 分段大小（字符数）
        chunk_overlap: 分段重叠大小（字符数）
        
    Returns:
        包含token估算信息的字典
    """
    # 估算字符数
    estimated_chars = int(file_size_bytes / 2.5)
    
    # 计算分段数
    effective_chunk_size = chunk_size - chunk_overlap
    estimated_chunks = math.ceil(estimated_chars / effective_chunk_size)
    
    # 每个chunk的字符数（平均）
    chars_per_chunk = estimated_chars / estimated_chunks
    
    # 每个chunk的输入token数
    # = prompt tokens + chunk文本tokens
    prompt_tokens_per_chunk = DEFAULT_PROMPT_TOKENS
    chunk_text_tokens = int(chars_per_chunk * CHARS_TO_TOKENS_RATIO)
    input_tokens_per_chunk = prompt_tokens_per_chunk + chunk_text_tokens
    
    # 总输入token数
    total_input_tokens = input_tokens_per_chunk * estimated_chunks
    
    # 输出token数（假设输出长度与输入文本长度相近，略少一些）
    # 因为校对通常不会大幅增加文本长度
    output_tokens_per_chunk = int(chunk_text_tokens * 0.95)  # 输出略少于输入
    total_output_tokens = output_tokens_per_chunk * estimated_chunks
    
    return {
        "file_size_bytes": file_size_bytes,
        "estimated_chars": estimated_chars,
        "estimated_chunks": estimated_chunks,
        "chars_per_chunk": int(chars_per_chunk),
        "input_tokens_per_chunk": input_tokens_per_chunk,
        "output_tokens_per_chunk": output_tokens_per_chunk,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
    }


def calculate_cost(token_info: dict, cache_hit_rate: float = 0.0) -> dict:
    """
    计算费用
    
    Args:
        token_info: token估算信息
        cache_hit_rate: 缓存命中率（0.0-1.0），默认0表示无缓存
        
    Returns:
        包含费用信息的字典
    """
    model = "deepseek-chat"
    pricing = DEEPSEEK_PRICING[model]
    
    # 计算输入token费用（考虑缓存）
    cache_hit_tokens = int(token_info["total_input_tokens"] * cache_hit_rate)
    cache_miss_tokens = token_info["total_input_tokens"] - cache_hit_tokens
    
    input_cost_cache_hit = (cache_hit_tokens / 1_000_000) * pricing["input_cache_hit"]
    input_cost_cache_miss = (cache_miss_tokens / 1_000_000) * pricing["input_cache_miss"]
    total_input_cost = input_cost_cache_hit + input_cost_cache_miss
    
    # 计算输出token费用
    total_output_cost = (token_info["total_output_tokens"] / 1_000_000) * pricing["output"]
    
    # 总费用
    total_cost = total_input_cost + total_output_cost
    
    return {
        "model": model,
        "cache_hit_rate": cache_hit_rate,
        "input_tokens": {
            "cache_hit": cache_hit_tokens,
            "cache_miss": cache_miss_tokens,
            "total": token_info["total_input_tokens"],
        },
        "output_tokens": token_info["total_output_tokens"],
        "total_tokens": token_info["total_tokens"],
        "costs": {
            "input_cache_hit": round(input_cost_cache_hit, 4),
            "input_cache_miss": round(input_cost_cache_miss, 4),
            "input_total": round(total_input_cost, 4),
            "output": round(total_output_cost, 4),
            "total_usd": round(total_cost, 4),
            "total_cny": round(total_cost * 7.2, 2),  # 假设汇率7.2
        },
        "pricing_info": {
            "input_cache_hit_per_m": pricing["input_cache_hit"],
            "input_cache_miss_per_m": pricing["input_cache_miss"],
            "output_per_m": pricing["output"],
        }
    }


def format_tokens(tokens: int) -> str:
    """格式化token数显示"""
    if tokens < 1000:
        return f"{tokens:,}"
    elif tokens < 1_000_000:
        return f"{tokens / 1000:.1f}K"
    else:
        return f"{tokens / 1_000_000:.2f}M"


if __name__ == "__main__":
    # 测试：2MB文件
    file_size = 2 * 1024 * 1024  # 2MB
    
    print("=" * 70)
    print("DeepSeek API 费用估算 - 2MB TXT文件")
    print("=" * 70)
    
    # 估算token
    token_info = estimate_tokens(file_size)
    
    print(f"\n文件信息:")
    print(f"  文件大小: {file_size / (1024*1024):.2f} MB")
    print(f"  估算字符数: {token_info['estimated_chars']:,}")
    print(f"  估算分段数: {token_info['estimated_chunks']}")
    print(f"  每段字符数: {token_info['chars_per_chunk']:,}")
    
    print(f"\nToken估算:")
    print(f"  每段输入token: {format_tokens(token_info['input_tokens_per_chunk'])}")
    print(f"  每段输出token: {format_tokens(token_info['output_tokens_per_chunk'])}")
    print(f"  总输入token: {format_tokens(token_info['total_input_tokens'])}")
    print(f"  总输出token: {format_tokens(token_info['total_output_tokens'])}")
    print(f"  总token数: {format_tokens(token_info['total_tokens'])}")
    
    # 计算费用（无缓存）
    print(f"\n费用估算（无缓存，cache_hit_rate=0%）:")
    cost_info_no_cache = calculate_cost(token_info, cache_hit_rate=0.0)
    print(f"  输入token (缓存未命中): {format_tokens(cost_info_no_cache['input_tokens']['cache_miss'])}")
    print(f"  输出token: {format_tokens(cost_info_no_cache['output_tokens'])}")
    print(f"  输入费用: ${cost_info_no_cache['costs']['input_total']:.4f}")
    print(f"  输出费用: ${cost_info_no_cache['costs']['output']:.4f}")
    print(f"  总费用: ${cost_info_no_cache['costs']['total_usd']:.4f} USD")
    print(f"  总费用: ¥{cost_info_no_cache['costs']['total_cny']:.2f} CNY")
    
    # 计算费用（50%缓存命中）
    print(f"\n费用估算（50%缓存命中，cache_hit_rate=50%）:")
    cost_info_50_cache = calculate_cost(token_info, cache_hit_rate=0.5)
    print(f"  输入token (缓存命中): {format_tokens(cost_info_50_cache['input_tokens']['cache_hit'])}")
    print(f"  输入token (缓存未命中): {format_tokens(cost_info_50_cache['input_tokens']['cache_miss'])}")
    print(f"  输出token: {format_tokens(cost_info_50_cache['output_tokens'])}")
    print(f"  输入费用: ${cost_info_50_cache['costs']['input_total']:.4f}")
    print(f"  输出费用: ${cost_info_50_cache['costs']['output']:.4f}")
    print(f"  总费用: ${cost_info_50_cache['costs']['total_usd']:.4f} USD")
    print(f"  总费用: ¥{cost_info_50_cache['costs']['total_cny']:.2f} CNY")
    
    # 计算费用（90%缓存命中，DeepSeek自动缓存）
    print(f"\n费用估算（90%缓存命中，cache_hit_rate=90%，DeepSeek自动缓存）:")
    cost_info_90_cache = calculate_cost(token_info, cache_hit_rate=0.9)
    print(f"  输入token (缓存命中): {format_tokens(cost_info_90_cache['input_tokens']['cache_hit'])}")
    print(f"  输入token (缓存未命中): {format_tokens(cost_info_90_cache['input_tokens']['cache_miss'])}")
    print(f"  输出token: {format_tokens(cost_info_90_cache['output_tokens'])}")
    print(f"  输入费用: ${cost_info_90_cache['costs']['input_total']:.4f}")
    print(f"  输出费用: ${cost_info_90_cache['costs']['output']:.4f}")
    print(f"  总费用: ${cost_info_90_cache['costs']['total_usd']:.4f} USD")
    print(f"  总费用: ¥{cost_info_90_cache['costs']['total_cny']:.2f} CNY")
    
    print(f"\n定价参考（DeepSeek-Chat）:")
    print(f"  输入 (缓存命中): ${cost_info_no_cache['pricing_info']['input_cache_hit_per_m']:.3f}/M tokens")
    print(f"  输入 (缓存未命中): ${cost_info_no_cache['pricing_info']['input_cache_miss_per_m']:.3f}/M tokens")
    print(f"  输出: ${cost_info_no_cache['pricing_info']['output_per_m']:.3f}/M tokens")
    
    print(f"\n提示:")
    print(f"  - DeepSeek支持自动上下文缓存，相同内容可节省90%输入费用")
    print(f"  - 新用户有500万免费token额度")
    print(f"  - 以上估算基于中文文本，实际可能因文本内容有所差异")

"""pycorrector 封装：仅 Ollama 路径使用，第一轮纠错。支持 kenlm（默认）/ macbert / gpt，懒加载，run_in_executor 调用。"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 懒加载：按 model 类型缓存实例，避免在非 Ollama 路径导入
_correctors = {}
_warned_missing = False  # 仅首次打印缺失依赖提示，避免刷屏


def _get_corrector(model: Optional[str] = None):
    """同步获取 corrector 实例（仅在 executor 或首次调用时使用）。"""
    resolved = (model or "kenlm").strip().lower()
    if resolved not in ("kenlm", "macbert", "gpt"):
        resolved = "kenlm"
    if resolved in _correctors:
        return _correctors[resolved]
    try:
        if resolved == "kenlm":
            from pycorrector import Corrector
            inst = Corrector()
            _correctors["kenlm"] = inst
            return inst
        if resolved == "macbert":
            try:
                from pycorrector import MacBertCorrector
                inst = MacBertCorrector("shibing624/macbert4csc-base-chinese")
                _correctors["macbert"] = inst
                return inst
            except Exception as e:
                logger.warning("[pycorrector] MacBert 加载失败，回退 Kenlm: %s", e)
                return _get_corrector("kenlm")
        if resolved == "gpt":
            try:
                from pycorrector.gpt.gpt_corrector import GptCorrector
                inst = GptCorrector()
                _correctors["gpt"] = inst
                return inst
            except Exception as e:
                logger.warning("[pycorrector] GptCorrector 加载失败，回退 Kenlm: %s", e)
                return _get_corrector("kenlm")
    except ImportError as e:
        global _warned_missing
        if not _warned_missing:
            _warned_missing = True
            logger.warning(
                "[pycorrector] 未安装或依赖缺失: %s。若需使用 Ollama 预纠错，请安装: pip install torch",
                e,
            )
        return None
    return None


def correct_sentence_sync(sentence: str, model: Optional[str] = None) -> str:
    """
    同步纠错单句。在 run_in_executor 中调用，避免阻塞事件循环。
    model 为 None 时使用 config.settings.ollama_pycorrector_model。
    异常或未安装时返回原文。
    """
    if not sentence or not sentence.strip():
        return sentence
    try:
        import config
        m = model or getattr(config.settings, "ollama_pycorrector_model", "kenlm")
        corrector = _get_corrector(m)
        if corrector is None:
            return sentence
        # Kenlm/Corrector: result = correct(text) -> dict with 'target','source','errors'
        # MacBertCorrector/GptCorrector: correct() 可能返回 dict 或 (text, details)
        result = corrector.correct(sentence)
        if isinstance(result, dict):
            return result.get("target", result.get("source", sentence))
        if isinstance(result, (list, tuple)) and len(result) >= 1:
            return result[0] if isinstance(result[0], str) else sentence
        return sentence
    except Exception as e:
        logger.warning("[pycorrector] 纠错异常，返回原文: %s", e)
        return sentence


async def correct_sentence(sentence: str, model: Optional[str] = None) -> str:
    """
    异步纠错单句：在 executor 中运行同步 correct，不阻塞事件循环。
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: correct_sentence_sync(sentence, model),
    )

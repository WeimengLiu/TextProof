"""FastAPI主应用"""
import sys
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import datetime as dt
from fastapi.responses import StreamingResponse
import io
from services.correction_service import CorrectionService
from services.task_manager import task_manager
from utils.diff_utils import highlight_diff, has_meaningful_changes
import config
import asyncio

logger = logging.getLogger(__name__)

app = FastAPI(title="小说文本精校系统", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求/响应模型
class CorrectionRequest(BaseModel):
    text: str
    provider: Optional[str] = None
    model_name: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None


class DiffRequest(BaseModel):
    text: str
    corrected: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None


class CorrectionResponse(BaseModel):
    original: str
    corrected: str
    chunks_processed: int
    total_chunks: int
    has_changes: bool
    failed_chunks: Optional[int] = 0
    has_failures: Optional[bool] = False
    failure_details: Optional[List[Dict[str, Any]]] = None


class DiffResponse(BaseModel):
    original_segments: list
    corrected_segments: list
    has_changes: bool

class ManualResultRequest(BaseModel):
    original: str
    corrected: str
    filename: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    provider: str
    model_name: str
    available: bool


# 全局服务实例（可根据请求参数动态创建）
_services: Dict[str, CorrectionService] = {}


def get_service(
    provider: Optional[str] = None,
    model_name: Optional[str] = None
) -> CorrectionService:
    """获取或创建校对服务实例"""
    key = f"{provider or 'default'}:{model_name or 'default'}"
    
    if key not in _services:
        _services[key] = CorrectionService(
            provider=provider,
            model_name=model_name
        )
    
    return _services[key]


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "小说文本精校系统",
        "version": "1.0.0",
        "description": "用于对网络下载的小说进行最小侵入式精校"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(
    provider: Optional[str] = None,
    model_name: Optional[str] = None
):
    """健康检查"""
    try:
        service = get_service(provider, model_name)
        available = await service.health_check()
        
        return HealthResponse(
            status="ok" if available else "unavailable",
            provider=provider or config.settings.default_model_provider,
            model_name=model_name or config.settings.default_model_name,
            available=available
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/correct", response_model=CorrectionResponse)
async def correct_text(request: CorrectionRequest):
    """
    校对文本
    
    请求体：
    - text: 待校对的文本
    - provider: 模型提供商（可选）
    - model_name: 模型名称（可选）
    - chunk_size: 分段大小（可选）
    - chunk_overlap: 分段重叠大小（可选）
    """
    logger.info("[API] /api/correct called")
    logger.info("[API] Provider: %s, Model: %s", request.provider, request.model_name)
    logger.info("[API] Text length: %d characters", len(request.text))
    logger.info("[API] Chunk size: %s, Overlap: %s", request.chunk_size, request.chunk_overlap)
    
    try:
        service = get_service(
            provider=request.provider,
            model_name=request.model_name
        )
        
        # 如果指定了chunk参数，创建临时服务实例
        if request.chunk_size or request.chunk_overlap:
            service = CorrectionService(
                provider=request.provider,
                model_name=request.model_name,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap
            )
        
        logger.info("[API] Starting text correction...")
        result = await service.correct_text(request.text)
        logger.info("[API] Text correction completed")
        logger.info("[API] Chunks processed: %d/%d", result.get('chunks_processed'), result.get('total_chunks'))
        logger.info("[API] Failed chunks: %d", result.get('failed_chunks', 0))
        
        # 检查是否有变化（忽略纯格式差异）
        has_changes = has_meaningful_changes(result["original"], result["corrected"])
        
        # 自动保存结果到比对结果列表（即使前端超时断开，结果也会保存）
        result_id = None
        try:
            now = dt.datetime.now()
            filename = f"输入框校对结果_{now.strftime('%Y%m%d_%H%M%S')}"
            result_id = task_manager.save_manual_result(
                filename=filename,
                original=result["original"],
                corrected=result["corrected"],
                has_changes=has_changes,
                provider=request.provider,
                model_name=request.model_name,
            )
            logger.info("[API] Result saved to database with result_id: %s", result_id)
        except Exception as e:
            # 保存失败不影响返回结果，仅记录日志
            logger.warning("[API] Failed to save result to database: %s", str(e))
        
        return CorrectionResponse(
            original=result["original"],
            corrected=result["corrected"],
            chunks_processed=result["chunks_processed"],
            total_chunks=result["total_chunks"],
            has_changes=has_changes,
            failed_chunks=result.get("failed_chunks", 0),
            has_failures=result.get("has_failures", False),
            failure_details=result.get("failure_details")
        )
    except Exception as e:
        logger.error("[API] Correction failed: %s", str(e))
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"校对失败: {str(e)}")


async def process_task_async(task_id: str, text: str, provider: Optional[str], model_name: Optional[str], use_chapters: bool = False):
    """异步处理任务"""
    try:
        service = get_service(provider, model_name)
        task = task_manager.get_task(task_id)
        
        if not task:
            return
        
        if use_chapters:
            # 按章节处理
            from utils.chapter_splitter import ChapterSplitter
            chapter_splitter = ChapterSplitter()
            chapters = chapter_splitter.split_by_chapters(text)
            
            # 更新任务信息
            task_manager.tasks[task_id]["total_chapters"] = len(chapters)
            
            corrected_chapters = []
            total_chunks = 0
            processed_chunks = 0
            
            for chapter in chapters:
                chapter_index = chapter["chapter_index"]
                chapter_title = chapter["chapter_title"]
                chapter_content = chapter["chapter_content"]
                
                # 更新章节状态为处理中
                task_manager.update_chapter_status(task_id, chapter_index, "processing", chapter_title)
                
                # 处理章节
                def chapter_progress_callback(current: int, total: int):
                    task_manager.update_task_progress(
                        task_id,
                        processed_chunks + current,
                        total_chunks,
                        chapter_index,
                        chapter_title
                    )
                
                chapter_result = await service.correct_text(chapter_content, progress_callback=chapter_progress_callback)
                
                # 检查章节是否有失败
                has_failures = chapter_result.get("has_failures", False)
                failed_chunks = chapter_result.get("failed_chunks", 0)
                
                # 更新章节状态
                if has_failures and failed_chunks == chapter_result.get("total_chunks", 0):
                    # 所有片段都失败
                    task_manager.update_chapter_status(task_id, chapter_index, "failed", chapter_title)
                else:
                    # 完成（可能有部分失败）
                    task_manager.update_chapter_status(task_id, chapter_index, "completed", chapter_title)
                
                corrected_chapters.append({
                    "chapter_index": chapter_index,
                    "chapter_title": chapter_title,
                    "original": chapter_result["original"],
                    "corrected": chapter_result["corrected"],
                    "has_changes": has_meaningful_changes(chapter_result["original"], chapter_result["corrected"]),
                    "chunks_processed": chapter_result["chunks_processed"],
                    "total_chunks": chapter_result["total_chunks"],
                    "failed_chunks": failed_chunks,
                    "has_failures": has_failures,
                })
                
                processed_chunks += chapter_result["total_chunks"]
                total_chunks += chapter_result["total_chunks"]
            
            # 合并所有章节（包含章节标题）
            original_text = "\n\n".join([
                f"{ch['chapter_title']}\n\n{ch['original']}" 
                for ch in corrected_chapters
            ])
            corrected_text = "\n\n".join([
                f"{ch['chapter_title']}\n\n{ch['corrected']}" 
                for ch in corrected_chapters
            ])
            has_changes = any(ch["has_changes"] for ch in corrected_chapters)
            
            task_manager.complete_task(task_id, original_text, corrected_text, has_changes, corrected_chapters)
        else:
            # 普通处理
            def progress_callback(current: int, total: int):
                task_manager.update_task_progress(task_id, current, total)
            
            result = await service.correct_text(text, progress_callback=progress_callback)
            
            has_changes = has_meaningful_changes(result["original"], result["corrected"])
            task_manager.complete_task(task_id, result["original"], result["corrected"], has_changes)
    except Exception as e:
        task_manager.fail_task(task_id, str(e))


@app.post("/api/correct/file")
async def correct_file(
    file: UploadFile = File(...),
    provider: Optional[str] = Query(None),
    model_name: Optional[str] = Query(None),
    async_task: bool = Query(False)  # 从查询参数获取
):
    """
    上传文件进行校对
    
    支持的文件格式：TXT
    
    参数:
    - async_task: 是否以后台任务方式处理（默认false，同步处理）
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="仅支持TXT文件")
    
    try:
        # 读取文件内容
        content = await file.read()
        text = content.decode('utf-8')
        file_size = len(content)
        
        # 如果启用后台任务
        if async_task:
            # 检测是否应该按章节处理（自动检测）
            from utils.chapter_splitter import ChapterSplitter
            chapter_splitter = ChapterSplitter()
            chapter_info = chapter_splitter.detect_chapters(text)
            use_chapters = chapter_info["has_chapters"] and chapter_info["chapter_count"] > 1
            
            # 创建任务
            task_id = task_manager.create_task(
                filename=file.filename,
                file_size=file_size,
                provider=provider,
                model_name=model_name,
                use_chapters=use_chapters
            )
            
            # 启动后台任务
            asyncio.create_task(process_task_async(task_id, text, provider, model_name, use_chapters))
            
            response = {
                "task_id": task_id,
                "message": "任务已创建，正在后台处理",
                "async": True
            }
            
            if use_chapters:
                response["use_chapters"] = True
                response["chapter_count"] = chapter_info["chapter_count"]
                response["message"] = f"任务已创建，检测到{chapter_info['chapter_count']}个章节，正在按章节处理"
            
            return response
        else:
            # 同步处理
            service = get_service(provider, model_name)
            result = await service.correct_text(text)
            
            has_changes = has_meaningful_changes(result["original"], result["corrected"])
            
            return CorrectionResponse(
                original=result["original"],
                corrected=result["corrected"],
                chunks_processed=result["chunks_processed"],
                total_chunks=result["total_chunks"],
                has_changes=has_changes
            )
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用UTF-8编码")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"校对失败: {str(e)}")


@app.post("/api/diff", response_model=DiffResponse)
async def get_diff(request: DiffRequest):
    """
    获取文本差异对比
    
    请求体：
    - text: 原文
    - corrected: 校对后的文本（如果提供，则使用；否则先校对再对比）
    - provider: 模型提供商（可选）
    - model_name: 模型名称（可选）
    """
    try:
        # 如果没有提供corrected，先进行校对
        if not request.corrected:
            service = get_service(
                provider=request.provider,
                model_name=request.model_name
            )
            correction_result = await service.correct_text(request.text)
            corrected_text = correction_result["corrected"]
        else:
            corrected_text = request.corrected
        
        diff_result = highlight_diff(request.text, corrected_text)
        
        return DiffResponse(
            original_segments=diff_result["original_segments"],
            corrected_segments=diff_result["corrected_segments"],
            has_changes=diff_result["has_changes"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"差异计算失败: {str(e)}")


@app.get("/api/providers")
async def get_providers():
    """获取可用的模型提供商列表"""
    from models.factory import ModelAdapterFactory
    return {
        "providers": ModelAdapterFactory.get_available_providers(),
        "default": config.settings.default_model_provider
    }


@app.get("/api/models")
async def get_models(provider: Optional[str] = None):
    """
    获取可用的模型列表
    
    参数:
    - provider: 模型提供商（可选），如果不提供则返回所有提供商的模型
    """
    if provider:
        models = config.settings.get_models_by_provider(provider)
        return {
            "provider": provider,
            "models": models,
            "default": config.settings.default_model_name if provider == config.settings.default_model_provider else None
        }
    else:
        all_models = config.settings.get_all_models()
        return {
            "models": all_models,
            "default_provider": config.settings.default_model_provider,
            "default_model": config.settings.default_model_name
        }


@app.get("/api/prompt")
async def get_prompt(reload: bool = Query(False)):
    """
    获取当前使用的Prompt
    
    参数:
    - reload: 是否重新从文件加载（默认false，使用缓存）
    """
    from utils.prompt_manager import prompt_manager
    return {
        "prompt": prompt_manager.get_prompt(reload=reload),
        "is_custom": config.settings.prompt_file is not None,
        "prompt_file": config.settings.prompt_file,
    }


@app.post("/api/prompt")
async def update_prompt(request: Dict[str, Any]):
    """
    更新Prompt
    
    请求体:
    - prompt: 新的Prompt文本
    - persist: 是否持久化保存（默认false）
    """
    from utils.prompt_manager import prompt_manager
    import os
    
    if "prompt" not in request:
        raise HTTPException(status_code=400, detail="缺少prompt字段")
    
    prompt_text = request["prompt"]
    persist = request.get("persist", False)
    
    # 更新Prompt
    prompt_manager.set_prompt(prompt_text)
    
    message = "Prompt已更新并立即生效"
    prompt_file_path = None
    
    if persist:
        try:
            # 保存到默认文件
            saved_path = prompt_manager.save_prompt_to_default_file()
            prompt_file_path = saved_path
            
            # 更新.env文件中的PROMPT_FILE配置
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            env_path = os.path.join(backend_dir, ".env")
            
            if os.path.exists(env_path):
                # 读取现有.env文件
                with open(env_path, "r", encoding="utf-8") as f:
                    env_lines = f.readlines()
                
                # 更新或添加PROMPT_FILE配置
                new_lines = []
                prompt_file_updated = False
                relative_path = "./prompts/custom_prompt.txt"
                
                for line in env_lines:
                    stripped = line.strip()
                    if stripped.startswith("PROMPT_FILE="):
                        new_lines.append(f"PROMPT_FILE={relative_path}\n")
                        prompt_file_updated = True
                    else:
                        new_lines.append(line)
                
                # 如果没有找到PROMPT_FILE，添加到Prompt配置区域
                if not prompt_file_updated:
                    # 查找Prompt配置区域或文件末尾
                    added = False
                    for i, line in enumerate(new_lines):
                        if "# Prompt配置" in line or "# Prompt" in line:
                            # 在Prompt配置区域添加
                            j = i + 1
                            while j < len(new_lines) and new_lines[j].strip().startswith("#"):
                                j += 1
                            new_lines.insert(j, f"PROMPT_FILE={relative_path}\n")
                            added = True
                            break
                    
                    if not added:
                        # 添加到文件末尾
                        new_lines.append(f"\n# Prompt配置\nPROMPT_FILE={relative_path}\n")
                
                # 写入文件
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
            
            message = f"Prompt已更新并立即生效，已保存到文件并更新.env配置（重启后也会生效）"
        except Exception as e:
            message = f"Prompt已更新并立即生效，但保存文件失败: {str(e)}"
    else:
        message = "Prompt已更新并立即生效（重启后恢复为配置文件中的Prompt）"
    
    return {
        "message": message,
        "prompt": prompt_manager.get_prompt(),
        "persisted": persist,
        "prompt_file": prompt_file_path,
    }


@app.get("/api/config")
async def get_config():
    """获取系统配置信息"""
    return {
        "chunk_size": config.settings.chunk_size,
        "chunk_overlap": config.settings.chunk_overlap,
        "ollama_chunk_size": config.settings.ollama_chunk_size,
        "ollama_chunk_overlap": config.settings.ollama_chunk_overlap,
        "fast_provider_max_chars": getattr(config.settings, "fast_provider_max_chars", 10000),
        "max_retries": config.settings.max_retries,
        "retry_delay": config.settings.retry_delay,
        "default_provider": config.settings.default_model_provider,
        "default_model": config.settings.default_model_name,
        "openai_models": config.settings.openai_models,
        "deepseek_models": config.settings.deepseek_models,
        "ollama_models": config.settings.ollama_models,
    }


@app.post("/api/config")
async def update_config(request: Dict[str, Any]):
    """
    更新系统配置
    
    请求体:
    - chunk_size: 文本分段大小（可选）
    - chunk_overlap: 分段重叠大小（可选）
    - ollama_chunk_size: Ollama专用分段大小（可选，针对本地大模型）
    - ollama_chunk_overlap: Ollama专用分段重叠大小（可选）
    - fast_provider_max_chars: 云端大模型整段直发阈值（字符数，可选）
    - max_retries: 最大重试次数（可选）
    - retry_delay: 重试延迟（可选）
    - default_provider: 默认模型提供商（可选）
    - default_model: 默认模型名称（可选）
    - openai_models: OpenAI模型列表（可选）
    - deepseek_models: DeepSeek模型列表（可选）
    - ollama_models: Ollama模型列表（可选）
    - persist: 是否持久化到.env文件（默认false，仅运行时更新）
    """
    update_data = {}
    
    # 验证并准备更新数据
    if "chunk_size" in request:
        chunk_size = int(request["chunk_size"])
        if chunk_size <= 0:
            raise HTTPException(status_code=400, detail="chunk_size必须大于0")
        update_data["chunk_size"] = chunk_size
    
    if "chunk_overlap" in request:
        chunk_overlap = int(request["chunk_overlap"])
        if chunk_overlap < 0:
            raise HTTPException(status_code=400, detail="chunk_overlap不能小于0")
        update_data["chunk_overlap"] = chunk_overlap
    
    if "ollama_chunk_size" in request:
        ollama_chunk_size = int(request["ollama_chunk_size"])
        if ollama_chunk_size <= 0:
            raise HTTPException(status_code=400, detail="ollama_chunk_size必须大于0")
        update_data["ollama_chunk_size"] = ollama_chunk_size
    
    if "ollama_chunk_overlap" in request:
        ollama_chunk_overlap = int(request["ollama_chunk_overlap"])
        if ollama_chunk_overlap < 0:
            raise HTTPException(status_code=400, detail="ollama_chunk_overlap不能小于0")
        update_data["ollama_chunk_overlap"] = ollama_chunk_overlap
    
    if "fast_provider_max_chars" in request:
        fast_provider_max_chars = int(request["fast_provider_max_chars"])
        if fast_provider_max_chars <= 0:
            raise HTTPException(status_code=400, detail="fast_provider_max_chars必须大于0")
        update_data["fast_provider_max_chars"] = fast_provider_max_chars
    
    if "max_retries" in request:
        max_retries = int(request["max_retries"])
        if max_retries < 0:
            raise HTTPException(status_code=400, detail="max_retries不能小于0")
        update_data["max_retries"] = max_retries
    
    if "retry_delay" in request:
        retry_delay = float(request["retry_delay"])
        if retry_delay < 0:
            raise HTTPException(status_code=400, detail="retry_delay不能小于0")
        update_data["retry_delay"] = retry_delay
    
    if "default_provider" in request:
        update_data["default_model_provider"] = request["default_provider"]
    
    if "default_model" in request:
        update_data["default_model_name"] = request["default_model"]
    
    if "openai_models" in request:
        update_data["openai_models"] = request["openai_models"]
    
    if "deepseek_models" in request:
        update_data["deepseek_models"] = request["deepseek_models"]
    
    if "ollama_models" in request:
        update_data["ollama_models"] = request["ollama_models"]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供要更新的配置项")
    
    # 更新配置
    persist = request.get("persist", False)
    
    try:
        # 先更新运行时配置
        config.settings.update_runtime_config(**update_data)

        # 配置更新后，清空已缓存的服务实例，确保下次调用使用最新配置
        # 尤其是依赖 chunk_size / ollama_chunk_size 等在 __init__ 中初始化的对象
        global _services
        _services.clear()
        
        if persist:
            # 持久化到.env文件
            success = config.settings.save_to_env_file()
            if success:
                message = "配置已更新并立即生效，同时已保存到.env文件（重启后也会生效）"
            else:
                message = "配置已更新并立即生效，但保存到.env文件失败，请检查文件权限"
        else:
            # 仅运行时更新
            message = "配置已更新并立即生效（重启后恢复为.env文件中的值）"
        
        return {
            "message": message,
            "persisted": persist,
            "config": {
                "chunk_size": config.settings.chunk_size,
                "chunk_overlap": config.settings.chunk_overlap,
                "ollama_chunk_size": config.settings.ollama_chunk_size,
                "ollama_chunk_overlap": config.settings.ollama_chunk_overlap,
                "fast_provider_max_chars": getattr(config.settings, "fast_provider_max_chars", 10000),
                "max_retries": config.settings.max_retries,
                "retry_delay": config.settings.retry_delay,
                "default_provider": config.settings.default_model_provider,
                "default_model": config.settings.default_model_name,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@app.get("/api/tasks")
async def get_tasks():
    """获取所有任务列表"""
    tasks = task_manager.get_all_tasks()
    return {"tasks": tasks}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.get("/api/results")
async def get_results():
    """获取所有比对结果列表"""
    # Pagination (production)
    # Keep response shape compatible: still returns {"results": [...]}
    # Extra: {"total","limit","offset"}
    try:
        # default: first page
        page = task_manager.store.list_results(limit=50, offset=0)
        return {"results": page.items, "total": page.total, "limit": page.limit, "offset": page.offset}
    except Exception:
        # fallback (should not happen)
        results = task_manager.get_all_results()
        return {"results": results}


@app.get("/api/results/{result_id}")
async def get_result(result_id: str, include_text: bool = Query(True)):
    """获取比对结果详情"""
    # Production default: include_text=True for backward compatibility with current frontend.
    # For very large results, client can set include_text=false then use download endpoint.
    result = task_manager.store.get_result(result_id=result_id, include_text=include_text, include_chapter_meta=True)
    if not result:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 如果结果很大，简化返回（前端可以单独请求章节）
    if result.get("use_chapters") and result.get("chapters"):
        chapters = result["chapters"]
        # 章节元数据来自 store，只有 original_length/corrected_length，无 original/corrected 文本
        total_original = sum(ch.get("original_length", 0) for ch in chapters)
        total_corrected = sum(ch.get("corrected_length", 0) for ch in chapters)
        simplified_result = {
            "result_id": result["result_id"],
            "task_id": result.get("task_id"),
            "filename": result["filename"],
            "has_changes": result["has_changes"],
            "use_chapters": True,
            "chapter_count": len(chapters),
            "original_length": total_original,
            "corrected_length": total_corrected,
            "provider": result.get("provider"),
            "model_name": result.get("model_name"),
            "chapters": [
                {
                    "chapter_index": ch["chapter_index"],
                    "chapter_title": ch["chapter_title"],
                    "has_changes": ch.get("has_changes", False),
                    "original_length": ch.get("original_length", 0),
                    "corrected_length": ch.get("corrected_length", 0),
                }
                for ch in chapters
            ],
            "created_at": result["created_at"],
            "completed_at": result.get("completed_at"),
        }
        return simplified_result
    
    return result


@app.get("/api/results/{result_id}/chapters/{chapter_index}")
async def get_chapter_result(result_id: str, chapter_index: int):
    """获取指定章节的比对结果"""
    meta = task_manager.store.get_result(result_id=result_id, include_text=False, include_chapter_meta=False)
    if not meta:
        raise HTTPException(status_code=404, detail="结果不存在")
    if not meta.get("use_chapters"):
        raise HTTPException(status_code=400, detail="该结果不是按章节处理的")
    chapter = task_manager.store.get_chapter(result_id=result_id, chapter_index=chapter_index)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@app.delete("/api/results/{result_id}")
async def delete_result(result_id: str):
    """删除比对结果"""
    success = task_manager.store.delete_result(result_id=result_id)
    if not success:
        raise HTTPException(status_code=404, detail="结果不存在")
    return {"message": "结果已删除", "result_id": result_id}


@app.post("/api/results/manual")
async def save_manual_result(request: ManualResultRequest):
    """保存“输入框直接校对”的比对结果到结果列表"""
    if not request.original or not request.corrected:
        raise HTTPException(status_code=400, detail="original 和 corrected 不能为空")

    filename = request.filename or f"输入框校对结果_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    has_changes = has_meaningful_changes(request.original, request.corrected)

    result_id = task_manager.save_manual_result(
        filename=filename,
        original=request.original,
        corrected=request.corrected,
        has_changes=has_changes,
        provider=request.provider,
        model_name=request.model_name,
    )
    return {"message": "结果已保存", "result_id": result_id}


@app.get("/api/results/{result_id}/download")
async def download_result(
    result_id: str,
    which: str = Query("corrected"),
    chapter_index: Optional[int] = Query(None),
):
    """
    下载结果文本（流式输出，生产友好）
    - which: original | corrected
    - chapter_index: 章节索引（仅章节结果）
    """
    if which not in ("original", "corrected"):
        raise HTTPException(status_code=400, detail="which 必须是 original 或 corrected")

    meta = task_manager.store.get_result(result_id=result_id, include_text=False, include_chapter_meta=False)
    if not meta:
        raise HTTPException(status_code=404, detail="结果不存在")

    filename_base = meta.get("filename") or result_id

    if meta.get("use_chapters"):
        if chapter_index is None:
            raise HTTPException(status_code=400, detail="该结果按章节处理，请提供 chapter_index")
        chapter = task_manager.store.get_chapter(result_id=result_id, chapter_index=int(chapter_index))
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")
        text = chapter.get(which) or ""
        chapter_title = chapter.get("chapter_title") or f"chapter_{chapter_index}"
        download_name = f"{filename_base}_{chapter_title}_{which}.txt"
    else:
        full = task_manager.store.get_result(result_id=result_id, include_text=True, include_chapter_meta=False)
        text = (full or {}).get(which) or ""
        download_name = f"{filename_base}_{which}.txt"

    data = text.encode("utf-8")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename=\"{download_name}\"'},
    )


if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="启动文本精校系统后端服务")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开发模式：启用热重载（代码修改后自动重启）"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="监听地址（默认: 0.0.0.0）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口（默认: 8000）"
    )
    parser.add_argument(
        "--reload-dir",
        type=str,
        default=None,
        help="监听重载的目录（默认: 当前目录）"
    )
    
    args = parser.parse_args()
    
    reload_dirs = [os.path.dirname(os.path.abspath(__file__))]
    if args.reload_dir:
        reload_dirs.append(args.reload_dir)
    
    if args.dev:
        logger.info("=" * 60)
        logger.info("🚀 启动开发模式（热重载已启用）")
        logger.info("📍 地址: http://%s:%d", args.host, args.port)
        logger.info("📁 监听目录: %s", ', '.join(reload_dirs))
        logger.info("💡 代码修改后会自动重启服务")
        logger.info("=" * 60)
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            reload=args.dev,
            reload_dirs=reload_dirs if args.dev else None,
            log_level="info"
        )
    else:
        logger.info("=" * 60)
        logger.info("🚀 启动生产模式")
        logger.info("📍 地址: http://%s:%d", args.host, args.port)
        logger.info("💡 使用 --dev 参数启用开发模式（热重载）")
        logger.info("=" * 60)
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info"
        )

"""FastAPI主应用"""
import sys
import os

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.correction_service import CorrectionService
from utils.diff_utils import highlight_diff
import config

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


class DiffResponse(BaseModel):
    original_segments: list
    corrected_segments: list
    has_changes: bool


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
        
        result = await service.correct_text(request.text)
        
        # 检查是否有变化
        has_changes = result["original"] != result["corrected"]
        
        return CorrectionResponse(
            original=result["original"],
            corrected=result["corrected"],
            chunks_processed=result["chunks_processed"],
            total_chunks=result["total_chunks"],
            has_changes=has_changes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"校对失败: {str(e)}")


@app.post("/api/correct/file")
async def correct_file(
    file: UploadFile = File(...),
    provider: Optional[str] = None,
    model_name: Optional[str] = None
):
    """
    上传文件进行校对
    
    支持的文件格式：TXT
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="仅支持TXT文件")
    
    try:
        # 读取文件内容
        content = await file.read()
        text = content.decode('utf-8')
        
        service = get_service(provider, model_name)
        result = await service.correct_text(text)
        
        has_changes = result["original"] != result["corrected"]
        
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
async def get_prompt():
    """获取当前使用的Prompt"""
    from utils.prompt_manager import prompt_manager
    return {
        "prompt": prompt_manager.get_prompt(),
        "is_custom": config.settings.prompt_file is not None,
        "prompt_file": config.settings.prompt_file,
    }


@app.post("/api/prompt")
async def update_prompt(request: Dict[str, Any]):
    """
    更新Prompt（仅运行时有效，重启后恢复）
    
    请求体:
    - prompt: 新的Prompt文本
    """
    from utils.prompt_manager import prompt_manager
    
    if "prompt" not in request:
        raise HTTPException(status_code=400, detail="缺少prompt字段")
    
    prompt_manager.set_prompt(request["prompt"])
    
    return {
        "message": "Prompt已更新",
        "prompt": prompt_manager.get_prompt(),
    }


@app.get("/api/config")
async def get_config():
    """获取系统配置信息"""
    return {
        "chunk_size": config.settings.chunk_size,
        "chunk_overlap": config.settings.chunk_overlap,
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
        
        if persist:
            # 持久化到.env文件
            success = config.settings.save_to_env_file()
            if success:
                message = "配置已更新并保存到.env文件，重启服务后生效"
            else:
                message = "配置已更新（运行时有效），但保存到.env文件失败，请检查文件权限"
        else:
            # 仅运行时更新
            message = "配置已更新（运行时有效，重启后恢复为.env文件中的值）"
        
        return {
            "message": message,
            "persisted": persist,
            "config": {
                "chunk_size": config.settings.chunk_size,
                "chunk_overlap": config.settings.chunk_overlap,
                "max_retries": config.settings.max_retries,
                "retry_delay": config.settings.retry_delay,
                "default_provider": config.settings.default_model_provider,
                "default_model": config.settings.default_model_name,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

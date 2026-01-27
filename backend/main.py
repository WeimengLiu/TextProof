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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

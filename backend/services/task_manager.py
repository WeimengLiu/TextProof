"""任务管理模块"""
import os
import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime
from enum import Enum

from services.storage.sqlite_store import SqliteStore


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"  # 等待中
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class TaskManager:
    """任务管理器"""
    
    def __init__(self, cache_dir: str = None):
        """
        初始化任务管理器
        
        Args:
            cache_dir: 缓存目录路径（默认：backend/cache）
        """
        if cache_dir is None:
            # 默认使用backend目录下的cache文件夹
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(backend_dir, "cache")
        
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.cache_dir = cache_dir
        self.store = SqliteStore(cache_dir=cache_dir)
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
    
    def create_task(
        self,
        filename: str,
        file_size: int,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        use_chapters: bool = False
    ) -> str:
        """
        创建新任务
        
        Args:
            filename: 文件名
            file_size: 文件大小（字节）
            provider: 模型提供商
            model_name: 模型名称
            use_chapters: 是否按章节处理
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "task_id": task_id,
            "filename": filename,
            "file_size": file_size,
            "status": TaskStatus.PENDING,
            "provider": provider,
            "model_name": model_name,
            "use_chapters": use_chapters,
            "progress": {
                "current": 0,
                "total": 0,
            },
            "chapter_progress": {} if use_chapters else None,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
        }
        # Persist task (best-effort)
        try:
            self.store.upsert_task(self.tasks[task_id])
        except Exception:
            pass
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def update_task_progress(
        self,
        task_id: str,
        current: int,
        total: int,
        chapter_index: Optional[int] = None,
        chapter_title: Optional[str] = None
    ):
        """更新任务进度"""
        if task_id in self.tasks:
            self.tasks[task_id]["progress"]["current"] = current
            self.tasks[task_id]["progress"]["total"] = total
            
            # 更新章节进度
            if chapter_index is not None and self.tasks[task_id].get("use_chapters"):
                if self.tasks[task_id]["chapter_progress"] is None:
                    self.tasks[task_id]["chapter_progress"] = {}
                
                if chapter_index not in self.tasks[task_id]["chapter_progress"]:
                    self.tasks[task_id]["chapter_progress"][chapter_index] = {
                        "chapter_index": chapter_index,
                        "chapter_title": chapter_title or f"第{chapter_index}章",
                        "status": "processing",
                        "progress": {"current": 0, "total": 0},
                    }
                
                self.tasks[task_id]["chapter_progress"][chapter_index]["progress"]["current"] = current
                self.tasks[task_id]["chapter_progress"][chapter_index]["progress"]["total"] = total
            
            if self.tasks[task_id]["status"] == TaskStatus.PENDING:
                self.tasks[task_id]["status"] = TaskStatus.PROCESSING
                self.tasks[task_id]["started_at"] = datetime.now().isoformat()

            # Persist task update (best-effort)
            try:
                self.store.upsert_task(self.tasks[task_id])
            except Exception:
                pass
    
    def update_chapter_status(
        self,
        task_id: str,
        chapter_index: int,
        status: str,
        chapter_title: Optional[str] = None
    ):
        """更新章节状态"""
        if task_id in self.tasks and self.tasks[task_id].get("use_chapters"):
            if self.tasks[task_id]["chapter_progress"] is None:
                self.tasks[task_id]["chapter_progress"] = {}
            
            if chapter_index not in self.tasks[task_id]["chapter_progress"]:
                self.tasks[task_id]["chapter_progress"][chapter_index] = {
                    "chapter_index": chapter_index,
                    "chapter_title": chapter_title or f"第{chapter_index}章",
                    "status": status,
                    "progress": {"current": 0, "total": 0},
                }
            else:
                self.tasks[task_id]["chapter_progress"][chapter_index]["status"] = status
                if chapter_title:
                    self.tasks[task_id]["chapter_progress"][chapter_index]["chapter_title"] = chapter_title
            # Persist task update (best-effort)
            try:
                self.store.upsert_task(self.tasks[task_id])
            except Exception:
                pass
    
    def complete_task(
        self,
        task_id: str,
        original: str,
        corrected: str,
        has_changes: bool,
        chapters: Optional[List[Dict[str, Any]]] = None
    ):
        """完成任务"""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = TaskStatus.COMPLETED
            self.tasks[task_id]["completed_at"] = datetime.now().isoformat()
            self.tasks[task_id]["progress"]["current"] = self.tasks[task_id]["progress"]["total"]
            
            # Persist task update (best-effort)
            try:
                self.store.upsert_task(self.tasks[task_id])
            except Exception:
                pass

            # Save result to SQLite
            result_id = task_id  # keep compatibility: task_id == result_id for async tasks
            use_chapters = bool(chapters)
            self.store.upsert_result(
                result_id=result_id,
                task_id=task_id,
                source="task",
                filename=self.tasks[task_id]["filename"],
                provider=self.tasks[task_id].get("provider"),
                model_name=self.tasks[task_id].get("model_name"),
                has_changes=has_changes,
                use_chapters=use_chapters,
                created_at=self.tasks[task_id]["created_at"],
                completed_at=self.tasks[task_id]["completed_at"],
                original_text=original,
                corrected_text=corrected,
            )
            if chapters:
                self.store.replace_chapters(result_id, chapters)

    def save_manual_result(
        self,
        filename: str,
        original: str,
        corrected: str,
        has_changes: bool,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """
        保存“输入框直接校对”的结果到缓存（results.json）
        
        Returns:
            result_id
        """
        result_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        self.store.upsert_result(
            result_id=result_id,
            task_id=None,
            source="manual_input",
            filename=filename,
            provider=provider,
            model_name=model_name,
            has_changes=has_changes,
            use_chapters=False,
            created_at=now,
            completed_at=now,
            original_text=original,
            corrected_text=corrected,
        )
        return result_id
    
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = TaskStatus.FAILED
            self.tasks[task_id]["completed_at"] = datetime.now().isoformat()
            self.tasks[task_id]["error"] = error
            try:
                self.store.upsert_task(self.tasks[task_id])
            except Exception:
                pass
    
    def get_all_tasks(self) -> list:
        """获取所有任务（按创建时间倒序）"""
        # Combine in-memory live tasks + persisted history (best-effort)
        tasks = list(self.tasks.values())
        try:
            page = self.store.list_tasks(limit=500, offset=0)
            persisted = page.items
            # Merge: in-memory overrides persisted for same task_id
            by_id = {t["task_id"]: t for t in persisted if t.get("task_id")}
            for t in tasks:
                by_id[t["task_id"]] = t
            merged = list(by_id.values())
            merged.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return merged
        except Exception:
            tasks.sort(key=lambda x: x["created_at"], reverse=True)
            return tasks
    
    def get_all_results(self) -> list:
        """获取所有结果（按完成时间倒序）"""
        page = self.store.list_results(limit=200, offset=0)
        return page.items
    
    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """获取结果详情"""
        # Default behavior used by existing endpoints: include text for non-chapter
        return self.store.get_result(result_id=result_id, include_text=True, include_chapter_meta=True)
    
    def delete_result(self, result_id: str) -> bool:
        """
        删除结果
        
        Returns:
            是否删除成功
        """
        return self.store.delete_result(result_id=result_id)
    
    def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务（保留最近N天的）"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        task_ids_to_remove = []
        for task_id, task in self.tasks.items():
            created_at = datetime.fromisoformat(task["created_at"])
            if created_at < cutoff:
                task_ids_to_remove.append(task_id)
        
        for task_id in task_ids_to_remove:
            del self.tasks[task_id]


# 全局任务管理器实例
task_manager = TaskManager()

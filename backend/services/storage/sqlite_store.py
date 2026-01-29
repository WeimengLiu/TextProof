"""SQLite storage for tasks/results (production-grade).

Goals:
- Avoid single huge JSON file writes.
- Support large texts safely (store in TEXT, stream out for download).
- Provide pagination and optional text inclusion to avoid huge payloads by default.
- Provide one-time migration from legacy `backend/cache/results.json`.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Page:
    items: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class SqliteStore:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.db_path = os.path.join(self.cache_dir, "textproof.db")
        self._lock = threading.Lock()
        self._init_db()
        self._maybe_migrate_legacy_results_json()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                # Pragmas for production-ish single-node
                cur.execute("PRAGMA journal_mode=WAL;")
                cur.execute("PRAGMA synchronous=NORMAL;")
                cur.execute("PRAGMA foreign_keys=ON;")

                # Schema versioning (minimal)
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                    """
                )

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS results (
                        result_id TEXT PRIMARY KEY,
                        task_id TEXT,
                        source TEXT NOT NULL,              -- task | manual_input
                        filename TEXT NOT NULL,
                        provider TEXT,
                        model_name TEXT,
                        has_changes INTEGER NOT NULL,
                        use_chapters INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        completed_at TEXT,
                        original_text TEXT,
                        corrected_text TEXT,
                        original_length INTEGER NOT NULL DEFAULT 0,
                        corrected_length INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chapters (
                        result_id TEXT NOT NULL,
                        chapter_index INTEGER NOT NULL,
                        chapter_title TEXT NOT NULL,
                        has_changes INTEGER NOT NULL DEFAULT 0,
                        original_text TEXT,
                        corrected_text TEXT,
                        original_length INTEGER NOT NULL DEFAULT 0,
                        corrected_length INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (result_id, chapter_index),
                        FOREIGN KEY (result_id) REFERENCES results(result_id) ON DELETE CASCADE
                    )
                    """
                )

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_size INTEGER NOT NULL DEFAULT 0,
                        provider TEXT,
                        model_name TEXT,
                        use_chapters INTEGER NOT NULL DEFAULT 0,
                        progress_current INTEGER NOT NULL DEFAULT 0,
                        progress_total INTEGER NOT NULL DEFAULT 0,
                        chapter_progress_json TEXT,
                        error TEXT,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT
                    )
                    """
                )

                cur.execute("CREATE INDEX IF NOT EXISTS idx_results_completed_at ON results(completed_at);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_results_task_id ON results(task_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);")
                conn.commit()
            finally:
                conn.close()

    # ----------------------------
    # Legacy migration (results.json)
    # ----------------------------
    def _maybe_migrate_legacy_results_json(self) -> None:
        legacy_path = os.path.join(self.cache_dir, "results.json")
        legacy_bak = os.path.join(self.cache_dir, "results.json.bak")
        if not os.path.exists(legacy_path) or os.path.exists(legacy_bak):
            return

        # Only migrate if DB has no results yet
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(1) AS c FROM results;")
                row = cur.fetchone()
                if row and int(row["c"]) > 0:
                    return
            finally:
                conn.close()

        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                legacy = json.load(f)  # dict[result_id] -> result_data
        except Exception:
            return

        # Migrate
        for _, result in (legacy or {}).items():
            try:
                self.upsert_result_from_legacy(result)
            except Exception:
                # Best-effort: skip bad rows
                continue

        # Backup old file to avoid repeated migration
        try:
            shutil.move(legacy_path, legacy_bak)
        except Exception:
            pass

    def upsert_result_from_legacy(self, result: Dict[str, Any]) -> None:
        result_id = result.get("result_id")
        if not result_id:
            return
        chapters = result.get("chapters")
        use_chapters = bool(result.get("use_chapters")) or bool(chapters)
        original = result.get("original") or ""
        corrected = result.get("corrected") or ""
        orig_len: Optional[int] = None
        corr_len: Optional[int] = None
        if chapters:
            orig_len = sum(len(ch.get("original") or "") for ch in chapters)
            corr_len = sum(len(ch.get("corrected") or "") for ch in chapters)
        self.upsert_result(
            result_id=result_id,
            task_id=result.get("task_id"),
            source=result.get("source") or ("task" if result.get("task_id") else "manual_input"),
            filename=result.get("filename") or "未知文件",
            provider=result.get("provider"),
            model_name=result.get("model_name"),
            has_changes=bool(result.get("has_changes")),
            use_chapters=use_chapters,
            created_at=result.get("created_at") or result.get("completed_at") or "",
            completed_at=result.get("completed_at"),
            original_text=original,
            corrected_text=corrected,
            original_length=orig_len,
            corrected_length=corr_len,
        )
        if chapters:
            self.replace_chapters(result_id, chapters)

    # ----------------------------
    # Results CRUD
    # ----------------------------
    def upsert_result(
        self,
        *,
        result_id: str,
        task_id: Optional[str],
        source: str,
        filename: str,
        provider: Optional[str],
        model_name: Optional[str],
        has_changes: bool,
        use_chapters: bool,
        created_at: str,
        completed_at: Optional[str],
        original_text: str,
        corrected_text: str,
        original_length: Optional[int] = None,
        corrected_length: Optional[int] = None,
    ) -> None:
        ol = original_length if original_length is not None else len(original_text or "")
        cl = corrected_length if corrected_length is not None else len(corrected_text or "")
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO results (
                        result_id, task_id, source, filename, provider, model_name,
                        has_changes, use_chapters, created_at, completed_at,
                        original_text, corrected_text, original_length, corrected_length
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(result_id) DO UPDATE SET
                        task_id=excluded.task_id,
                        source=excluded.source,
                        filename=excluded.filename,
                        provider=excluded.provider,
                        model_name=excluded.model_name,
                        has_changes=excluded.has_changes,
                        use_chapters=excluded.use_chapters,
                        created_at=excluded.created_at,
                        completed_at=excluded.completed_at,
                        original_text=excluded.original_text,
                        corrected_text=excluded.corrected_text,
                        original_length=excluded.original_length,
                        corrected_length=excluded.corrected_length
                    """,
                    (
                        result_id,
                        task_id,
                        source,
                        filename,
                        provider,
                        model_name,
                        1 if has_changes else 0,
                        1 if use_chapters else 0,
                        created_at,
                        completed_at,
                        original_text,
                        corrected_text,
                        ol,
                        cl,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list_results(self, *, limit: int, offset: int) -> Page:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(1) AS c FROM results;")
                total = int(cur.fetchone()["c"])
                cur.execute(
                    """
                    SELECT
                        result_id, task_id, filename, provider, model_name, source,
                        has_changes, use_chapters, created_at, completed_at,
                        original_length, corrected_length
                    FROM results
                    ORDER BY COALESCE(completed_at, created_at) DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                items = []
                for r in cur.fetchall():
                    items.append(
                        {
                            "result_id": r["result_id"],
                            "task_id": r["task_id"],
                            "filename": r["filename"],
                            "provider": r["provider"],
                            "model_name": r["model_name"],
                            "source": r["source"],
                            "has_changes": bool(r["has_changes"]),
                            "use_chapters": bool(r["use_chapters"]),
                            "created_at": r["created_at"],
                            "completed_at": r["completed_at"],
                            "original_length": int(r["original_length"] or 0),
                            "corrected_length": int(r["corrected_length"] or 0),
                        }
                    )

                # Fill chapter_count for chapter results (best-effort; small N)
                for item in items:
                    if item.get("use_chapters"):
                        cur.execute(
                            "SELECT COUNT(1) AS c FROM chapters WHERE result_id = ?;",
                            (item["result_id"],),
                        )
                        item["chapter_count"] = int(cur.fetchone()["c"])

                return Page(items=items, total=total, limit=limit, offset=offset)
            finally:
                conn.close()

    def get_result(
        self,
        *,
        result_id: str,
        include_text: bool,
        include_chapter_meta: bool = True,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM results WHERE result_id = ?;", (result_id,))
                r = cur.fetchone()
                if not r:
                    return None
                out: Dict[str, Any] = {
                    "result_id": r["result_id"],
                    "task_id": r["task_id"],
                    "filename": r["filename"],
                    "provider": r["provider"],
                    "model_name": r["model_name"],
                    "source": r["source"],
                    "has_changes": bool(r["has_changes"]),
                    "use_chapters": bool(r["use_chapters"]),
                    "created_at": r["created_at"],
                    "completed_at": r["completed_at"],
                    "original_length": int(r["original_length"] or 0),
                    "corrected_length": int(r["corrected_length"] or 0),
                }
                if include_text and not out["use_chapters"]:
                    out["original"] = r["original_text"] or ""
                    out["corrected"] = r["corrected_text"] or ""

                if out["use_chapters"] and include_chapter_meta:
                    cur.execute(
                        """
                        SELECT chapter_index, chapter_title, has_changes, original_length, corrected_length
                        FROM chapters
                        WHERE result_id = ?
                        ORDER BY chapter_index ASC
                        """,
                        (result_id,),
                    )
                    chapters = []
                    for ch in cur.fetchall():
                        chapters.append(
                            {
                                "chapter_index": int(ch["chapter_index"]),
                                "chapter_title": ch["chapter_title"],
                                "has_changes": bool(ch["has_changes"]),
                                "original_length": int(ch["original_length"] or 0),
                                "corrected_length": int(ch["corrected_length"] or 0),
                            }
                        )
                    out["chapter_count"] = len(chapters)
                    out["chapters"] = chapters
                return out
            finally:
                conn.close()

    def get_chapter(self, *, result_id: str, chapter_index: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT chapter_index, chapter_title, has_changes, original_text, corrected_text FROM chapters WHERE result_id=? AND chapter_index=?;",
                    (result_id, int(chapter_index)),
                )
                ch = cur.fetchone()
                if not ch:
                    return None
                return {
                    "chapter_index": int(ch["chapter_index"]),
                    "chapter_title": ch["chapter_title"],
                    "has_changes": bool(ch["has_changes"]),
                    "original": ch["original_text"] or "",
                    "corrected": ch["corrected_text"] or "",
                }
            finally:
                conn.close()

    def delete_result(self, *, result_id: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM results WHERE result_id = ?;", (result_id,))
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
            finally:
                conn.close()

    def replace_chapters(self, result_id: str, chapters: List[Dict[str, Any]]) -> None:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM chapters WHERE result_id = ?;", (result_id,))
                for ch in chapters:
                    original = ch.get("original") or ""
                    corrected = ch.get("corrected") or ""
                    from utils.diff_utils import has_meaningful_changes
                    has_changes = bool(ch.get("has_changes")) if "has_changes" in ch else has_meaningful_changes(original, corrected)
                    cur.execute(
                        """
                        INSERT INTO chapters (
                            result_id, chapter_index, chapter_title, has_changes,
                            original_text, corrected_text, original_length, corrected_length
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            result_id,
                            int(ch.get("chapter_index") or 0),
                            ch.get("chapter_title") or "",
                            1 if has_changes else 0,
                            original,
                            corrected,
                            len(original),
                            len(corrected),
                        ),
                    )
                conn.commit()
            finally:
                conn.close()

    # ----------------------------
    # Tasks persistence (best-effort)
    # ----------------------------
    def upsert_task(self, task: Dict[str, Any]) -> None:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                progress = task.get("progress") or {}
                chapter_progress = task.get("chapter_progress")
                cur.execute(
                    """
                    INSERT INTO tasks (
                        task_id, status, filename, file_size, provider, model_name, use_chapters,
                        progress_current, progress_total, chapter_progress_json, error,
                        created_at, started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        status=excluded.status,
                        filename=excluded.filename,
                        file_size=excluded.file_size,
                        provider=excluded.provider,
                        model_name=excluded.model_name,
                        use_chapters=excluded.use_chapters,
                        progress_current=excluded.progress_current,
                        progress_total=excluded.progress_total,
                        chapter_progress_json=excluded.chapter_progress_json,
                        error=excluded.error,
                        created_at=excluded.created_at,
                        started_at=excluded.started_at,
                        completed_at=excluded.completed_at
                    """,
                    (
                        task.get("task_id"),
                        str(task.get("status")),
                        task.get("filename") or "",
                        int(task.get("file_size") or 0),
                        task.get("provider"),
                        task.get("model_name"),
                        1 if task.get("use_chapters") else 0,
                        int(progress.get("current") or 0),
                        int(progress.get("total") or 0),
                        json.dumps(chapter_progress, ensure_ascii=False) if chapter_progress is not None else None,
                        task.get("error"),
                        task.get("created_at") or "",
                        task.get("started_at"),
                        task.get("completed_at"),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list_tasks(self, *, limit: int = 200, offset: int = 0) -> Page:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(1) AS c FROM tasks;")
                total = int(cur.fetchone()["c"])
                cur.execute(
                    """
                    SELECT * FROM tasks
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                items = []
                for t in cur.fetchall():
                    chapter_progress = None
                    if t["chapter_progress_json"]:
                        try:
                            chapter_progress = json.loads(t["chapter_progress_json"])
                        except Exception:
                            chapter_progress = None
                    items.append(
                        {
                            "task_id": t["task_id"],
                            "filename": t["filename"],
                            "file_size": int(t["file_size"] or 0),
                            "status": t["status"],
                            "provider": t["provider"],
                            "model_name": t["model_name"],
                            "use_chapters": bool(t["use_chapters"]),
                            "progress": {"current": int(t["progress_current"] or 0), "total": int(t["progress_total"] or 0)},
                            "chapter_progress": chapter_progress,
                            "created_at": t["created_at"],
                            "started_at": t["started_at"],
                            "completed_at": t["completed_at"],
                            "error": t["error"],
                        }
                    )
                return Page(items=items, total=total, limit=limit, offset=offset)
            finally:
                conn.close()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM tasks WHERE task_id = ?;", (task_id,))
                t = cur.fetchone()
                if not t:
                    return None
                chapter_progress = None
                if t["chapter_progress_json"]:
                    try:
                        chapter_progress = json.loads(t["chapter_progress_json"])
                    except Exception:
                        chapter_progress = None
                return {
                    "task_id": t["task_id"],
                    "filename": t["filename"],
                    "file_size": int(t["file_size"] or 0),
                    "status": t["status"],
                    "provider": t["provider"],
                    "model_name": t["model_name"],
                    "use_chapters": bool(t["use_chapters"]),
                    "progress": {"current": int(t["progress_current"] or 0), "total": int(t["progress_total"] or 0)},
                    "chapter_progress": chapter_progress,
                    "created_at": t["created_at"],
                    "started_at": t["started_at"],
                    "completed_at": t["completed_at"],
                    "error": t["error"],
                }
            finally:
                conn.close()


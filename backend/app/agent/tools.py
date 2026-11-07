from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import ProjectFile
from app.services import vfs
from app.services.runs import RunEmitter

settings = get_settings()

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "update_plan",
            "description": "更新 3–6 步构建计划，用于前端实时展示。",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 6,
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "done"],
                                },
                            },
                            "required": ["title"],
                        },
                    }
                },
                "required": ["steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出当前工程的所有文件与大小。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取一个文件的完整内容。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "完整写入或覆盖一个文件。content 必须是完整文件内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "删除一个文件。入口文件 index.html 不允许删除。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "结束本次生成，并给出面向用户的中文总结。",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        },
    },
]

_ENTRY_PATH = "index.html"


@dataclass(slots=True)
class ToolOutcome:
    content: str
    finished: bool = False
    summary: str | None = None


def _summarize_arguments(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "write_file":
        content = str(arguments.get("content") or "")
        return {
            "path": str(arguments.get("path") or ""),
            "size": len(content.encode("utf-8")),
        }
    if name in ("read_file", "delete_file"):
        return {"path": str(arguments.get("path") or "")}
    if name == "update_plan":
        steps = arguments.get("steps") or []
        return {"steps": len(steps) if isinstance(steps, list) else 0}
    return {}


class AgentTools:
    def __init__(
        self,
        session: AsyncSession,
        project_id: str,
        emitter: RunEmitter,
    ) -> None:
        self._session = session
        self._project_id = project_id
        self._emitter = emitter

    async def execute(self, name: str, raw_arguments: str) -> ToolOutcome:
        try:
            arguments = json.loads(raw_arguments) if raw_arguments else {}
        except json.JSONDecodeError:
            return ToolOutcome(json.dumps({"error": "工具参数不是合法 JSON"}))
        if not isinstance(arguments, dict):
            return ToolOutcome(json.dumps({"error": "工具参数必须是对象"}))

        await self._emitter.emit(
            "tool.start",
            {"name": name, "arguments": _summarize_arguments(name, arguments)},
        )

        try:
            return await self._dispatch(name, arguments)
        except AppError as exc:
            return ToolOutcome(json.dumps({"error": exc.message}, ensure_ascii=False))

    async def _dispatch(self, name: str, arguments: dict[str, Any]) -> ToolOutcome:
        if name == "update_plan":
            return await self._update_plan(arguments)
        if name == "list_files":
            return await self._list_files()
        if name == "read_file":
            return await self._read_file(arguments)
        if name == "write_file":
            return await self._write_file(arguments)
        if name == "delete_file":
            return await self._delete_file(arguments)
        if name == "finish":
            return self._finish(arguments)
        return ToolOutcome(json.dumps({"error": f"未知工具：{name}"}))

    async def _update_plan(self, arguments: dict[str, Any]) -> ToolOutcome:
        raw_steps = arguments.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise AppError(422, "invalid_plan", "计划至少需要一步")
        steps: list[dict[str, str]] = []
        for raw in raw_steps[:6]:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()[:80]
            if not title:
                continue
            status = raw.get("status")
            if status not in ("pending", "in_progress", "done"):
                status = "pending"
            steps.append({"title": title, "status": status})
        await self._emitter.emit("plan.updated", {"steps": steps})
        return ToolOutcome(json.dumps({"ok": True, "steps": len(steps)}))

    async def _list_files(self) -> ToolOutcome:
        files = await vfs.list_files(self._session, self._project_id)
        payload = [{"path": file.path, "size": file.size} for file in files]
        return ToolOutcome(json.dumps(payload, ensure_ascii=False))

    async def _read_file(self, arguments: dict[str, Any]) -> ToolOutcome:
        path = vfs.validate_path(str(arguments.get("path") or ""))
        file = await vfs.get_file(self._session, self._project_id, path)
        if file is None:
            return ToolOutcome(json.dumps({"error": f"文件不存在：{path}"}, ensure_ascii=False))
        return ToolOutcome(file.content)

    async def _write_file(self, arguments: dict[str, Any]) -> ToolOutcome:
        raw_path = str(arguments.get("path") or "")
        content = arguments.get("content")
        if not isinstance(content, str):
            raise AppError(422, "invalid_content", "content 必须是字符串")
        path, old_content = await vfs.write_file(self._session, self._project_id, raw_path, content)
        size = len(content.encode("utf-8"))
        await self._session.commit()
        await self._emitter.emit(
            "file.updated",
            {
                "path": path,
                "size": size,
                "diff": vfs.unified_diff(old_content, content, path),
                "deleted": False,
            },
        )
        return ToolOutcome(json.dumps({"ok": True, "path": path, "size": size}))

    async def _delete_file(self, arguments: dict[str, Any]) -> ToolOutcome:
        path = vfs.validate_path(str(arguments.get("path") or ""))
        if path == _ENTRY_PATH:
            raise AppError(422, "entry_protected", "不能删除入口文件 index.html")
        deleted = await vfs.delete_file(self._session, self._project_id, path)
        if not deleted:
            return ToolOutcome(json.dumps({"error": f"文件不存在：{path}"}, ensure_ascii=False))
        await self._session.commit()
        await self._emitter.emit("file.updated", {"path": path, "deleted": True})
        return ToolOutcome(json.dumps({"ok": True, "deleted": path}))

    @staticmethod
    def _finish(arguments: dict[str, Any]) -> ToolOutcome:
        summary = str(arguments.get("summary") or "").strip()
        if not summary:
            summary = "本次生成已完成。"
        return ToolOutcome(json.dumps({"ok": True}), finished=True, summary=summary[:500])


def file_manifest(files: list[ProjectFile]) -> str:
    return "\n".join(f"- {file.path} ({file.size} bytes)" for file in files)

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.messages import (
    assistant_message,
    system_message,
    tool_message,
)
from app.agent.prompts import build_system_prompt
from app.agent.templates import pick_template
from app.agent.tools import TOOL_SCHEMAS, AgentTools
from app.agent.validation import validate_project
from app.core.config import get_settings
from app.db.models import Message, Project, Run
from app.db.session import SessionFactory
from app.services import runs as run_service
from app.services import versions as version_service
from app.services import vfs
from app.services.llm import LLMError, LLMGateway, MessageAccumulator, build_gateway
from app.services.llm.factory import resolve_mode
from app.services.runs import RunEmitter

settings = get_settings()
logger = structlog.get_logger()

_MAX_TRUNCATION_RETRIES = 2
_TRUNCATION_NUDGE = (
    "上一条输出因长度限制被截断。请缩小单次输出："
    "把大文件拆成多个文件（如 index.html + styles.css + app.js），"
    "单次 write_file 内容控制在约 6000 字符以内；先写骨架，再分步补充。"
    "不要输出与工具调用无关的长文本。"
)


class RunCancelled(Exception):
    pass


class AgentFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


async def execute_run(
    run_id: str,
    *,
    gateway: LLMGateway | None = None,
) -> None:
    async with SessionFactory() as session:
        run = await session.get(Run, run_id)
        if run is None:
            return
        project = await session.get(Project, run.project_id)
        if project is None or run.status in ("succeeded", "failed"):
            return

        emitter = RunEmitter(session, run_id, await run_service.max_event_seq(session, run_id))
        if run.status == "cancelled":
            await emitter.emit("run.status", {"status": "cancelled", "run_id": run_id})
            return

        await run_service.mark_running(session, run, project)
        await emitter.emit("run.status", {"status": "running", "run_id": run_id})

        started = time.monotonic()
        try:
            mode = resolve_mode()
            if mode == "demo":
                summary, tokens_in, tokens_out = await _run_demo(session, project, emitter)
            else:
                active_gateway = gateway or build_gateway()
                if active_gateway is None:
                    raise AgentFailure("llm_not_configured", "未配置 DeepSeek API Key")
                summary, tokens_in, tokens_out = await _run_agent(
                    session, run, project, emitter, active_gateway
                )
        except RunCancelled:
            await _mark_cancelled(session, run, project)
            await emitter.emit("run.status", {"status": "cancelled", "run_id": run_id})
            return
        except AgentFailure as exc:
            await _mark_failed(session, run, project, exc.code, exc.message)
            await emitter.emit("error", {"code": exc.code, "message": exc.message})
            await emitter.emit(
                "run.status",
                {"status": "failed", "run_id": run_id, "error": exc.message},
            )
            return
        except LLMError as exc:
            message = _public_message(str(exc))
            await _mark_failed(session, run, project, "llm_error", message)
            await emitter.emit("error", {"code": "llm_error", "message": message})
            await emitter.emit(
                "run.status", {"status": "failed", "run_id": run_id, "error": message}
            )
            return
        except Exception:
            logger.exception("run.unhandled_error", run_id=run_id)
            message = "生成过程中出现内部错误，请重试"
            await _mark_failed(session, run, project, "internal_error", message)
            await emitter.emit("error", {"code": "internal_error", "message": message})
            await emitter.emit(
                "run.status", {"status": "failed", "run_id": run_id, "error": message}
            )
            return

        if await _is_cancelled(session, run):
            await _mark_cancelled(session, run, project)
            await emitter.emit("run.status", {"status": "cancelled", "run_id": run_id})
            return

        files = await vfs.list_files(session, project.id)
        errors = validate_project(project, files)
        if errors:
            message = "；".join(errors)[:500]
            await _mark_failed(session, run, project, "validation_failed", message)
            await emitter.emit("error", {"code": "validation_failed", "message": message})
            await emitter.emit(
                "run.status", {"status": "failed", "run_id": run_id, "error": message}
            )
            return

        version = await version_service.create_version(
            session, project, files, label=summary or "Agent 生成"
        )
        project.status = "succeeded"
        _set_run_success(run, tokens_in, tokens_out)
        session.add(
            Message(project_id=project.id, role="assistant", content=summary, run_id=run.id)
        )
        await session.commit()

        duration_ms = int((time.monotonic() - started) * 1000)
        await emitter.emit(
            "preview.ready", {"version": version.number, "entry": project.entry_path}
        )
        await emitter.emit(
            "usage",
            {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "duration_ms": duration_ms,
                "mode": mode,
            },
        )
        await emitter.emit(
            "run.status",
            {
                "status": "succeeded",
                "run_id": run_id,
                "version": version.number,
                "mode": mode,
                "summary": summary,
            },
        )


async def _run_agent(
    session: AsyncSession,
    run: Run,
    project: Project,
    emitter: RunEmitter,
    gateway: LLMGateway,
) -> tuple[str, int, int]:
    files = await vfs.list_files(session, project.id)
    history = await _history(session, project.id)
    messages = [system_message(build_system_prompt(project, files))]
    messages.extend({"role": item.role, "content": item.content} for item in history)

    tools = AgentTools(session, project.id, emitter)
    summary = ""
    tokens_in = 0
    tokens_out = 0
    truncation_retries = 0

    for _step in range(settings.max_steps):
        if await _is_cancelled(session, run):
            raise RunCancelled

        accumulator = MessageAccumulator()
        async for chunk in gateway.stream_chat(
            messages=messages, tools=TOOL_SCHEMAS, max_tokens=8000
        ):
            text = accumulator.absorb(chunk)
            if text:
                await emitter.emit("assistant.delta", {"text": text})
        response = accumulator.response()
        tokens_in += response.usage.prompt_tokens
        tokens_out += response.usage.completion_tokens

        if response.finish_reason == "length":
            truncation_retries += 1
            if truncation_retries > _MAX_TRUNCATION_RETRIES:
                raise AgentFailure("output_truncated", "模型输出被截断，请缩小单个文件后重试")
            logger.warning(
                "agent.output_truncated",
                run_id=run.id,
                attempt=truncation_retries,
            )
            await emitter.emit(
                "assistant.delta",
                {"text": "\n输出过长，正在改用更小的文件重试…\n"},
            )
            messages.append({"role": "user", "content": _TRUNCATION_NUDGE})
            continue

        if not response.tool_calls:
            summary = response.content.strip()
            break

        messages.append(assistant_message(response.content, response.tool_calls))
        finished = False
        for call in response.tool_calls:
            if await _is_cancelled(session, run):
                raise RunCancelled
            outcome = await tools.execute(call.name, call.arguments)
            messages.append(tool_message(call.id, call.name, outcome.content))
            if outcome.finished:
                summary = outcome.summary or "本次生成已完成。"
                finished = True
                break
        if finished:
            break
    else:
        raise AgentFailure("step_limit", f"超过最大工具步数 {settings.max_steps}，请缩小需求后重试")

    if not summary:
        summary = "本次生成已完成。"
    return summary, tokens_in, tokens_out


async def _run_demo(
    session: AsyncSession, project: Project, emitter: RunEmitter
) -> tuple[str, int, int]:
    template = pick_template(project.prompt)
    tools = AgentTools(session, project.id, emitter)

    await emitter.emit(
        "assistant.delta",
        {"text": "当前未配置模型 Key，已切换到内置离线模板，保证流程可以完整体验。\n"},
    )
    await tools.execute(
        "update_plan",
        _json(
            {
                "steps": [
                    {"title": "理解需求并选择模板", "status": "done"},
                    {"title": "生成页面结构 index.html", "status": "in_progress"},
                    {"title": "编写样式与交互", "status": "pending"},
                    {"title": "校验并生成预览版本", "status": "pending"},
                ]
            }
        ),
    )
    for index, (path, content) in enumerate(template.files.items()):
        if await _is_cancelled_by_project(session, project.id):
            raise RunCancelled
        await tools.execute("write_file", _json({"path": path, "content": content}))
        if index == 0:
            await tools.execute(
                "update_plan",
                _json(
                    {
                        "steps": [
                            {"title": "理解需求并选择模板", "status": "done"},
                            {"title": "生成页面结构 index.html", "status": "done"},
                            {"title": "编写样式与交互", "status": "in_progress"},
                            {"title": "校验并生成预览版本", "status": "pending"},
                        ]
                    }
                ),
            )
    await tools.execute(
        "update_plan",
        _json(
            {
                "steps": [
                    {"title": "理解需求并选择模板", "status": "done"},
                    {"title": "生成页面结构 index.html", "status": "done"},
                    {"title": "编写样式与交互", "status": "done"},
                    {"title": "校验并生成预览版本", "status": "done"},
                ]
            }
        ),
    )
    summary = (
        f"已使用「{template.title}」演示模板生成可交互应用。"
        "配置 LLM_API_KEY 后将切换到 DeepSeek 实时生成。"
    )
    return summary, 0, 0


async def _history(session: AsyncSession, project_id: str) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.project_id == project_id, Message.run_id.is_not(None))
        .order_by(Message.id.asc())
        .limit(200)
    )
    return list(result.scalars().all())[-12:]


async def _is_cancelled(session: AsyncSession, run: Run) -> bool:
    return await run_service.is_run_cancelled(session, run.id)


async def _is_cancelled_by_project(session: AsyncSession, project_id: str) -> bool:
    result = await session.execute(
        select(Run.status)
        .where(Run.project_id == project_id, Run.status.in_(("queued", "running")))
        .limit(1)
    )
    status = result.scalar_one_or_none()
    return status is None or status == "cancelled"


def _set_run_success(run: Run, tokens_in: int, tokens_out: int) -> None:
    run.status = "succeeded"
    run.tokens_in = tokens_in
    run.tokens_out = tokens_out
    run.finished_at = datetime.now(UTC)


async def _mark_cancelled(session: AsyncSession, run: Run, project: Project) -> None:
    run.status = "cancelled"
    run.finished_at = datetime.now(UTC)
    project.status = "idle"
    await session.commit()


async def _mark_failed(
    session: AsyncSession, run: Run, project: Project, code: str, message: str
) -> None:
    run.status = "failed"
    run.error_code = code
    run.error_message = message[:500]
    run.finished_at = datetime.now(UTC)
    project.status = "failed"
    await session.commit()


def _public_message(message: str) -> str:
    return message.splitlines()[0][:300] if message else "模型调用失败"


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False)

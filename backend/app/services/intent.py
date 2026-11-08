from __future__ import annotations

import re
from typing import Literal

import structlog

from app.services.llm import LLMError, LLMGateway, MessageAccumulator

logger = structlog.get_logger()

type Intent = Literal["chat", "build"]

_BUILD_ACTIONS = (
    "做一个",
    "做个",
    "做成",
    "创建",
    "新建",
    "生成",
    "搭建",
    "开发",
    "实现",
    "编写",
    "写一个",
    "写个",
    "修改",
    "更改",
    "改成",
    "改为",
    "换成",
    "换掉",
    "替换",
    "调整",
    "添加",
    "增加",
    "加个",
    "加上",
    "加一个",
    "删除",
    "删掉",
    "去掉",
    "移除",
    "修复",
    "优化",
    "美化",
    "重构",
    "接入",
    "适配",
    "弄成",
    "搞成",
    "搞个",
    "补上",
    "补充",
    "完善",
    "重做",
    "改造",
    "改一下",
)
_BUILD_FILES = (".html", ".css", ".js", ".json", ".svg", ".md", ".txt")
_BUILD_ACTIONS_EN = re.compile(
    r"\b(create|build|generate|implement|refactor)\b",
    re.IGNORECASE,
)

_CHAT_CUES = (
    "你好",
    "您好",
    "嗨",
    "哈喽",
    "早上好",
    "中午好",
    "下午好",
    "晚上好",
    "晚安",
    "在吗",
    "在不在",
    "你是谁",
    "你叫什么",
    "介绍一下你自己",
    "你能做什么",
    "你会什么",
    "谢谢",
    "感谢",
    "辛苦了",
    "再见",
    "拜拜",
    "回头见",
    "讲个笑话",
    "说个笑话",
    "笑话",
    "聊聊天",
    "闲聊",
    "天气",
    "今天几号",
    "现在几点",
    "你吃饭了吗",
    "吃了吗",
)
_CHAT_CUES_EN = re.compile(
    r"\b(hi|hello|hey|thanks|thank you|bye|goodbye)\b",
    re.IGNORECASE,
)

_APP_SUBJECTS = (
    "页面",
    "网站",
    "应用",
    "网页",
    "界面",
    "布局",
    "样式",
    "颜色",
    "背景",
    "字体",
    "按钮",
    "导航",
    "菜单",
    "表单",
    "弹窗",
    "动画",
    "功能",
    "首页",
    "主页",
    "看板",
    "博客",
    "商城",
    "计算器",
    "待办",
    "文件",
    "代码",
    "预览",
    "版本",
    "分享",
    "导出",
    "html",
    "css",
    "js",
)
_APP_SUBJECTS_EN = re.compile(
    r"\b(app|website|webpage|page|ui|button|layout|style)\b",
    re.IGNORECASE,
)

_QUESTION = re.compile(r"[?？]\s*$")
_VISIBLE_TEXT = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]")

_INTENT_SYSTEM = """你是 Atom Demo 工作区的意图分类器。
用户会发来一条消息，请判断它是想创建或修改 Web 应用，还是普通聊天。
BUILD：要求创建、修改、修复、调整应用、页面、文件、样式、功能或交互。
CHAT：问候、寒暄、闲聊、与当前应用无关的问题、询问助手身份或能力、单纯感谢或确认。
如果无法确定，优先输出 BUILD，避免漏掉真实的应用需求。
只输出一个英文单词：BUILD 或 CHAT。"""


def classify_rule(message: str) -> Intent | None:
    """Fast deterministic pass; None means the input needs LLM review."""
    text = message.strip()
    if not text:
        return "chat"
    if not _VISIBLE_TEXT.search(text):
        return "chat"

    lowered = text.lower()
    if any(action in text for action in _BUILD_ACTIONS):
        return "build"
    if _BUILD_ACTIONS_EN.search(text):
        return "build"
    if any(extension in lowered for extension in _BUILD_FILES):
        return "build"

    if any(cue in text for cue in _CHAT_CUES) or _CHAT_CUES_EN.search(text):
        return "chat"

    if _QUESTION.search(text) and not _mentions_app(lowered):
        return "chat"
    return None


async def classify(
    message: str,
    *,
    gateway: LLMGateway | None,
    project_title: str,
    has_files: bool,
) -> Intent:
    rule = classify_rule(message)
    if rule is not None:
        return rule
    if gateway is None:
        return "build"
    try:
        return await review_intent(
            message,
            gateway=gateway,
            project_title=project_title,
            has_files=has_files,
        )
    except LLMError:
        logger.warning("intent.review_failed", project_title=project_title)
        return "build"


async def review_intent(
    message: str,
    *,
    gateway: LLMGateway,
    project_title: str,
    has_files: bool,
) -> Intent:
    context = (
        f"项目：{project_title}\n"
        f"当前状态：{'已有生成文件' if has_files else '尚未生成'}\n"
        f"用户消息：{message}"
    )
    accumulator = MessageAccumulator()
    async for chunk in gateway.stream_chat(
        messages=[
            {"role": "system", "content": _INTENT_SYSTEM},
            {"role": "user", "content": context},
        ],
        tools=[],
        max_tokens=8,
    ):
        accumulator.absorb(chunk)
    return _parse_intent(accumulator.content)


def _parse_intent(content: str) -> Intent:
    words = set(re.findall(r"\b(BUILD|CHAT)\b", content.upper()))
    if words == {"CHAT"}:
        return "chat"
    return "build"


def _mentions_app(text: str) -> bool:
    return any(subject in text for subject in _APP_SUBJECTS) or bool(_APP_SUBJECTS_EN.search(text))

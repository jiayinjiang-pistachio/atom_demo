from __future__ import annotations

import posixpath
import re
from urllib.parse import urlsplit

from app.db.models import Project, ProjectFile

_REFERENCE_PATTERN = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_EXTERNAL_PREFIXES = ("http://", "https://", "//", "data:", "mailto:", "tel:")


def validate_project(project: Project, files: list[ProjectFile]) -> list[str]:
    errors: list[str] = []
    paths = {file.path for file in files}
    entry = next((file for file in files if file.path == project.entry_path), None)
    if entry is None:
        errors.append(f"缺少入口文件 {project.entry_path}")
        return errors
    if not entry.content.strip():
        errors.append(f"入口文件 {project.entry_path} 为空")

    empty = [file.path for file in files if not file.content.strip()]
    if empty:
        errors.append("以下文件内容为空：" + ", ".join(empty))

    if entry.path.endswith(".html"):
        errors.extend(_check_references(entry.path, entry.content, paths))

    for file in files:
        if file.path.endswith(".css"):
            errors.extend(_check_css_references(file.path, file.content, paths))

    return errors


def _check_references(owner: str, source: str, paths: set[str]) -> list[str]:
    missing: list[str] = []
    for match in _REFERENCE_PATTERN.finditer(source):
        reference = match.group(1).strip()
        if not reference or reference.startswith("#") or reference.startswith(_EXTERNAL_PREFIXES):
            continue
        if reference.startswith("/"):
            missing.append(reference)
            continue
        target = _resolve(owner, reference)
        if target and target not in paths:
            missing.append(reference)
    if not missing:
        return []
    return [f"{owner} 引用了不存在的文件：" + ", ".join(sorted(set(missing)))]


def _check_css_references(owner: str, source: str, paths: set[str]) -> list[str]:
    missing: list[str] = []
    for raw in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", source):
        reference = raw.strip()
        if (
            not reference
            or reference.startswith(_EXTERNAL_PREFIXES)
            or reference.startswith("data:")
        ):
            continue
        if reference.startswith("/"):
            missing.append(reference)
            continue
        target = _resolve(owner, reference)
        if target and target not in paths:
            missing.append(reference)
    if not missing:
        return []
    return [f"{owner} 引用了不存在的资源：" + ", ".join(sorted(set(missing)))]


def _resolve(owner: str, reference: str) -> str | None:
    parsed = urlsplit(reference)
    clean = posixpath.normpath(parsed.path)
    if clean.startswith(".."):
        return None
    base = posixpath.dirname(owner)
    resolved = posixpath.normpath(posixpath.join(base, clean)) if base else clean
    if resolved.startswith(".."):
        return None
    return resolved

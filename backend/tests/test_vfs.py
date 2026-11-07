import pytest

from app.core.errors import AppError
from app.services import vfs


@pytest.mark.parametrize(
    "path",
    ["index.html", "styles.css", "assets/app.js", "data/config.json", "notes/readme.md"],
)
def test_validate_path_accepts_relative_whitelisted_paths(path: str) -> None:
    assert vfs.validate_path(path) == path


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/etc/passwd",
        "../index.html",
        "assets/../../index.html",
        "assets\\app.js",
        "script.exe",
        "index.js?x=1",
        "a//b.html",
        ".hidden.html",
    ],
)
def test_validate_path_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(AppError) as caught:
        vfs.validate_path(path)
    assert caught.value.status_code == 422


def test_unified_diff_marks_new_file() -> None:
    diff = vfs.unified_diff(None, "<main>ok</main>\n", "index.html")

    assert "--- /dev/null" in diff
    assert "+++ b/index.html" in diff
    assert "+<main>ok</main>" in diff


def test_unified_diff_marks_changes() -> None:
    diff = vfs.unified_diff("a\nb\n", "a\nc\n", "app.js")

    assert "-b" in diff
    assert "+c" in diff

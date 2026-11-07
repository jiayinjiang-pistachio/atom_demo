from app.agent.validation import validate_project
from app.db.models import Project, ProjectFile


def _project() -> Project:
    return Project(
        id="01TEST0000000000000000000",
        owner_id="owner",
        title="t",
        prompt="p",
        entry_path="index.html",
    )


def _file(path: str, content: str) -> ProjectFile:
    return ProjectFile(project_id="01TEST0000000000000000000", path=path, content=content, size=1)


def test_validation_accepts_linked_files() -> None:
    project = _project()
    files = [
        _file(
            "index.html",
            '<link rel="stylesheet" href="styles.css"><script src="app.js"></script>',
        ),
        _file("styles.css", "body{color:red}"),
        _file("app.js", "console.log('ok')"),
    ]

    assert validate_project(project, files) == []


def test_validation_reports_missing_entry() -> None:
    project = _project()
    errors = validate_project(project, [_file("styles.css", "body{}")])

    assert any("缺少入口文件" in error for error in errors)


def test_validation_reports_missing_reference() -> None:
    project = _project()
    files = [_file("index.html", '<script src="missing.js"></script>')]

    errors = validate_project(project, files)
    assert any("missing.js" in error for error in errors)


def test_validation_ignores_external_references() -> None:
    project = _project()
    files = [_file("index.html", '<img src="https://example.com/a.png">')]

    assert validate_project(project, files) == []

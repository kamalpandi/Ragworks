"""Enforces the frontend/backend import boundary.

Both rules are active as of Phase 2 (task 3.4 removed the HTML branch from
app/api/v1/endpoints/eval.py): the frontend may not import backend internals,
and the backend may not import templating or the frontend.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "app" / "frontend"

# Backend modules a frontend file may never import.
FRONTEND_ALLOWED = (
    "app.frontend",
    "app.core.config",
    "app.core.csrf",
    "app.core.sessions",
)

BACKEND_DIRS = [
    "app/api",
    "app/services",
    "app/core",
    "app/components",
    "app/models",
    "app/evaluation",
    "app/observability",
    "app/middleware",
]
BACKEND_FORBIDDEN = ("jinja2", "starlette.templating", "app.frontend", "app.ui")


def iter_imports(path: Path):
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def frontend_violations(root: Path):
    violations = []
    for path in root.rglob("*.py"):
        for module in iter_imports(path):
            if not (module == "app" or module.startswith("app.")):
                continue
            if any(
                module == allowed or module.startswith(allowed + ".")
                for allowed in FRONTEND_ALLOWED
            ):
                continue
            violations.append((_rel(path), module))
    return violations


def backend_violations():
    violations = []
    for rel in BACKEND_DIRS:
        directory = REPO_ROOT / rel
        if not directory.exists():
            continue
        for path in directory.rglob("*.py"):
            for module in iter_imports(path):
                if any(
                    module == forbidden or module.startswith(forbidden + ".")
                    for forbidden in BACKEND_FORBIDDEN
                ):
                    violations.append((_rel(path), module))
    return violations


def test_frontend_imports_no_backend_internals():
    violations = frontend_violations(FRONTEND_DIR)
    assert violations == [], f"frontend imports backend internals: {violations}"


def test_scanner_detects_injected_frontend_violation(tmp_path):
    pkg = tmp_path / "app" / "frontend"
    pkg.mkdir(parents=True)
    (pkg / "bad.py").write_text("from app.services.ingestion import IngestionService\n")
    violations = frontend_violations(pkg)
    assert any(module.startswith("app.services") for _, module in violations)


def test_scanner_allows_shared_config(tmp_path):
    pkg = tmp_path / "app" / "frontend"
    pkg.mkdir(parents=True)
    (pkg / "ok.py").write_text("from app.core.config import settings\n")
    assert frontend_violations(pkg) == []


def test_backend_imports_no_templating_or_ui():
    violations = backend_violations()
    assert violations == [], f"backend imports templating/frontend/ui: {violations}"

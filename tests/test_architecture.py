"""Enforces the frontend/backend import boundary.

Both rules are active as of Phase 2 (task 3.4 removed the HTML branch from
app/api/v1/endpoints/eval.py): the frontend may not import backend internals,
and the backend may not import templating or the frontend.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = REPO_ROOT / "app"
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


# --- Row-factory convention -------------------------------------------------
#
# psycopg cursors return tuples unless opened with row_factory=dict_row. Reading
# a column by name (row["col"]) from a default cursor raises TypeError at
# request time, which is exactly how the usage aggregation 500s shipped. This
# guard flags any factory-less conn.cursor() whose fetched rows are indexed by
# string literal. Heuristic: it misses an aliased cursor indexed in another
# scope, which is acceptable — it catches the common shape.

ROW_FETCHERS = ("fetchone", "fetchall")


def _unwrap_await(node):
    while isinstance(node, ast.Await):
        node = node.value
    return node


def _has_dict_row_kw(call: ast.Call) -> bool:
    return any(
        kw.arg == "row_factory"
        and isinstance(kw.value, ast.Name)
        and kw.value.id == "dict_row"
        for kw in call.keywords
    )


def _is_plain_cursor(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "cursor"
        and not _has_dict_row_kw(node)
    )


def _is_fetch_call(node: ast.AST) -> bool:
    node = _unwrap_await(node)
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ROW_FETCHERS
    )


def _fetch_target_names(func: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and _is_fetch_call(node.value):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
            continue
        if isinstance(node, ast.AnnAssign):
            target, expr = node.target, node.value
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            target, expr = node.target, node.iter
        else:
            continue
        if _is_fetch_call(expr) and isinstance(target, ast.Name):
            names.add(target.id)
    return names


def _function_row_factory_violations(func: ast.AST) -> list[int]:
    if not any(isinstance(n, ast.Call) and _is_plain_cursor(n) for n in ast.walk(func)):
        return []
    names = _fetch_target_names(func)
    lines = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Subscript):
            continue
        if not (
            isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)
        ):
            continue
        value = node.value
        if (isinstance(value, ast.Name) and value.id in names) or _is_fetch_call(value):
            lines.append(node.lineno)
    return lines


def _has_connection_level_dict_row(tree: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "connect"
        and _has_dict_row_kw(n)
        for n in ast.walk(tree)
    )


def row_factory_violations(root: Path) -> list[tuple[str, int]]:
    violations = set()
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except SyntaxError:
            continue
        if _has_connection_level_dict_row(tree):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for lineno in _function_row_factory_violations(node):
                    violations.add((_rel(path), lineno))
    return sorted(violations)


def test_conn_cursor_reads_by_name_require_dict_row():
    violations = row_factory_violations(APP_DIR)
    assert violations == [], (
        "conn.cursor() reads columns by name without row_factory=dict_row: "
        f"{violations}"
    )


def test_row_factory_guard_detects_injected_violation(tmp_path):
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "bad.py").write_text(
        "async def f(pool):\n"
        "    async with pool.connection() as conn, conn.cursor() as cur:\n"
        "        for row in await cur.fetchall():\n"
        "            return row['x']\n"
    )
    assert row_factory_violations(pkg) != []


def test_row_factory_guard_allows_dict_row(tmp_path):
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "ok.py").write_text(
        "from psycopg.rows import dict_row\n"
        "async def f(pool):\n"
        "    async with pool.connection() as conn, "
        "conn.cursor(row_factory=dict_row) as cur:\n"
        "        for row in await cur.fetchall():\n"
        "            return row['x']\n"
    )
    assert row_factory_violations(pkg) == []

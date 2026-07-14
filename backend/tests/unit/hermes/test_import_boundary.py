# Governing constraint (task instruction, CRITICAL CONSTRAINTS): Hermes
# coordinates and monitors ONLY — it must never import from
# domain/strategy_engine, domain/portfolio, domain/execution, domain/risk
# (nor their application/persistence-repository counterparts, the same
# financial logic one layer over). This test statically parses every .py
# file under quant_hub/hermes/ and fails if any import statement references
# one of those packages — a real static guarantee, not just "nobody happened
# to import it in this PR."
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_HERMES_ROOT = Path(__file__).resolve().parents[3] / "src" / "quant_hub" / "hermes"

_FORBIDDEN_PREFIXES = (
    "quant_hub.domain.strategy_engine",
    "quant_hub.domain.portfolio",
    "quant_hub.domain.execution",
    "quant_hub.domain.risk",
    "quant_hub.application.strategy_engine",
    "quant_hub.application.portfolio",
    "quant_hub.application.execution",
    "quant_hub.application.risk",
    "quant_hub.application.trading",
    "quant_hub.persistence.repositories.strategy_engine",
    "quant_hub.persistence.repositories.portfolio",
    "quant_hub.persistence.repositories.execution",
    "quant_hub.persistence.repositories.risk",
)


def _hermes_source_files() -> list[Path]:
    assert _HERMES_ROOT.is_dir(), f"expected {_HERMES_ROOT} to exist"
    return sorted(_HERMES_ROOT.rglob("*.py"))


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize("path", _hermes_source_files(), ids=lambda p: str(p.relative_to(_HERMES_ROOT)))
def test_no_financial_pipeline_imports(path: Path) -> None:
    modules = _imported_modules(path.read_text(encoding="utf-8"))
    violations = {
        module
        for module in modules
        for forbidden in _FORBIDDEN_PREFIXES
        if module == forbidden or module.startswith(forbidden + ".")
    }
    assert not violations, f"{path.relative_to(_HERMES_ROOT)} imports barred financial-pipeline module(s): {violations}"


def test_hermes_package_has_files_to_check() -> None:
    # Guards against the parametrize silently collecting zero cases if the
    # package ever moves — an empty parametrize list would make the test
    # above vacuously "pass" without checking anything.
    assert len(_hermes_source_files()) >= 5

"""Layer 1: Structure rules (ATL001–ATL004)."""

from __future__ import annotations

from typing import Any

from toolint.core.ast_utils import MIN_FACADE_METHODS, find_assignments, find_classes, parse_file
from toolint.core.context import ProjectContext
from toolint.core.models import LintResult, Severity
from toolint.rules.registry import register


@register(
    "ATL001",
    name="facade-exists",
    description="Package must have a single public facade class",
    severity=Severity.ERROR,
    layer="structure",
)
def check_facade_exists(ctx: ProjectContext) -> list[LintResult]:
    """Check that the package has an identifiable facade class."""
    if not ctx.pkg_dir.is_dir():
        return [
            LintResult(
                rule_id="ATL001",
                severity=Severity.ERROR,
                message=f"Package directory '{ctx.config.package}/' not found.",
                hint="Set 'package' in [tool.toolint] or check pyproject.toml.",
            )
        ]

    # If facade_class is configured, check it exists
    if ctx.config.facade_class:
        return _check_configured_facade(ctx)

    # Auto-detect: find the class with the most public methods
    candidates = _find_facade_candidates(ctx)
    if not candidates:
        return [
            LintResult(
                rule_id="ATL001",
                severity=Severity.ERROR,
                message="No public facade class found in package.",
                hint=(
                    "Create a class that serves as the main public API, "
                    "or set 'facade_class' in [tool.toolint]."
                ),
            )
        ]

    return []


def _check_configured_facade(ctx: ProjectContext) -> list[LintResult]:
    """Check that the configured facade class actually exists."""
    for py_file in ctx.pkg_dir.rglob("*.py"):
        tree = parse_file(py_file)
        if tree is None:
            continue
        for cls in find_classes(tree):
            if cls["name"] == ctx.config.facade_class:
                return []

    return [
        LintResult(
            rule_id="ATL001",
            severity=Severity.ERROR,
            message=f"Configured facade class '{ctx.config.facade_class}' not found in package.",
            file=str(ctx.pkg_dir),
        )
    ]


def _find_facade_candidates(ctx: ProjectContext) -> list[dict[str, Any]]:
    """Find classes that look like facade classes (many public methods)."""
    candidates: list[dict[str, Any]] = []
    for py_file in ctx.pkg_dir.rglob("*.py"):
        # Skip core/, tests/, __init__.py
        rel = py_file.relative_to(ctx.pkg_dir)
        parts = rel.parts
        if any(p in ("core", "tests", "__pycache__") for p in parts):
            continue
        if py_file.name == "__init__.py":
            continue

        tree = parse_file(py_file)
        if tree is None:
            continue
        for cls in find_classes(tree):
            if cls["method_count"] >= MIN_FACADE_METHODS:
                candidates.append({**cls, "file": str(py_file)})

    return candidates


@register(
    "ATL002",
    name="main-module-exists",
    description="__main__.py must exist and be registered in pyproject.toml scripts",
    severity=Severity.ERROR,
    layer="structure",
)
def check_main_module(ctx: ProjectContext) -> list[LintResult]:
    """Check __main__.py exists."""
    results: list[LintResult] = []
    if not ctx.main_file.exists():
        results.append(
            LintResult(
                rule_id="ATL002",
                severity=Severity.ERROR,
                message=f"'{ctx.config.package}/__main__.py' not found.",
                hint="Create __main__.py as the CLI entry point.",
            )
        )
    return results


@register(
    "ATL003",
    name="init-all-exports",
    description="__init__.py must define __all__ including the facade class",
    severity=Severity.WARNING,
    layer="structure",
)
def check_init_all(ctx: ProjectContext) -> list[LintResult]:
    """Check __init__.py defines __all__ with facade class."""
    if not ctx.init_file.exists():
        return []

    tree = parse_file(ctx.init_file)
    if tree is None:
        return []

    results: list[LintResult] = []
    all_assigns = find_assignments(tree, "__all__")

    if not all_assigns:
        results.append(
            LintResult(
                rule_id="ATL003",
                severity=Severity.WARNING,
                message="__init__.py does not define __all__.",
                file=str(ctx.init_file),
                hint="Add __all__ to explicitly declare the public API.",
            )
        )
        return results

    # Check facade class is in __all__
    if ctx.config.facade_class:
        all_value = all_assigns[0]["value"]
        if isinstance(all_value, list) and ctx.config.facade_class not in all_value:
            results.append(
                LintResult(
                    rule_id="ATL003",
                    severity=Severity.WARNING,
                    message=f"Facade class '{ctx.config.facade_class}' not in __all__.",
                    file=str(ctx.init_file),
                    line=all_assigns[0]["line"],
                )
            )

    return results


@register(
    "ATL004",
    name="version-match",
    description="__version__ in __init__.py must match pyproject.toml version",
    severity=Severity.ERROR,
    layer="structure",
)
def check_version_match(ctx: ProjectContext) -> list[LintResult]:
    """Check __version__ matches pyproject.toml."""
    if not ctx.init_file.exists():
        return []

    tree = parse_file(ctx.init_file)
    if tree is None:
        return []

    # Get __version__ from __init__.py
    version_assigns = find_assignments(tree, "__version__")
    if not version_assigns:
        return [
            LintResult(
                rule_id="ATL004",
                severity=Severity.ERROR,
                message="__init__.py does not define __version__.",
                file=str(ctx.init_file),
            )
        ]

    init_version = version_assigns[0]["value"]

    # Get version from pyproject.toml
    pyproject_version = ctx.pyproject.get("tool", {}).get("poetry", {}).get(
        "version"
    ) or ctx.pyproject.get("project", {}).get("version")

    if pyproject_version and init_version != pyproject_version:
        return [
            LintResult(
                rule_id="ATL004",
                severity=Severity.ERROR,
                message=(
                    f"Version mismatch: __init__.py has '{init_version}' "
                    f"but pyproject.toml has '{pyproject_version}'"
                ),
                file=str(ctx.init_file),
                line=version_assigns[0]["line"],
            )
        ]

    return []

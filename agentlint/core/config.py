"""Configuration loader — reads from pyproject.toml or .agentlint.toml."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from agentlint.core.models import LintConfig

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]


def _find_pyproject(project_dir: Path) -> Path | None:
    path = project_dir / "pyproject.toml"
    return path if path.exists() else None


def _find_agentlint_toml(project_dir: Path) -> Path | None:
    path = project_dir / ".agentlint.toml"
    return path if path.exists() else None


def _detect_package(pyproject: dict[str, Any]) -> str:
    """Auto-detect package name from pyproject.toml."""
    # Poetry style
    poetry = pyproject.get("tool", {}).get("poetry", {})
    if poetry:
        packages = poetry.get("packages", [])
        if packages:
            return packages[0].get("include", "")
        name = poetry.get("name", "")
        if name:
            return name.replace("-", "_")

    # PEP 621 style
    project = pyproject.get("project", {})
    if project:
        name = project.get("name", "")
        if name:
            return name.replace("-", "_")

    return ""


def load_config(project_dir: Path) -> tuple[LintConfig, dict[str, Any]]:
    """Load lint config and raw pyproject data from the project directory.

    Returns (LintConfig, raw_pyproject_dict).
    """
    raw_pyproject: dict[str, Any] = {}
    config_data: dict[str, Any] = {}

    # Load pyproject.toml (always needed for rule checks)
    pyproject_path = _find_pyproject(project_dir)
    if pyproject_path:
        with open(pyproject_path, "rb") as f:
            raw_pyproject = tomllib.load(f)
        config_data = raw_pyproject.get("tool", {}).get("agentlint", {})

    # Override with .agentlint.toml if exists
    agentlint_path = _find_agentlint_toml(project_dir)
    if agentlint_path:
        with open(agentlint_path, "rb") as f:
            config_data = tomllib.load(f)

    # Build config
    defaults = LintConfig()
    cfg = LintConfig(
        package=config_data.get("package", "") or _detect_package(raw_pyproject),
        facade_class=config_data.get("facade_class", ""),
        core_dir=config_data.get("core_dir", "core"),
        interface_files=config_data.get("interface_files", defaults.interface_files),
        core_allowed_imports=config_data.get("core_allowed_imports", []),
        ignore=config_data.get("ignore", []),
        select=config_data.get("select", []),
    )

    return cfg, raw_pyproject

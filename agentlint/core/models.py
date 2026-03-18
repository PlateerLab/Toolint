"""Core data models for Agentlint — all stdlib, no external deps."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    """Lint issue severity level."""

    ERROR = "error"
    WARNING = "warning"

    def __str__(self) -> str:
        return self.value


@dataclass
class RuleDefinition:
    """Metadata for a single lint rule."""

    id: str  # e.g. "ATL001"
    name: str  # e.g. "facade-exists"
    description: str  # human-readable description
    severity: Severity
    layer: str  # e.g. "structure", "dependency", "pyproject"


@dataclass
class LintResult:
    """A single lint issue found during analysis."""

    rule_id: str
    severity: Severity
    message: str
    file: str = ""
    line: int = 0
    col: int = 0
    hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "rule_id": self.rule_id,
            "severity": str(self.severity),
            "message": self.message,
        }
        if self.file:
            d["file"] = self.file
        if self.line:
            d["line"] = self.line
        if self.col:
            d["col"] = self.col
        if self.hint:
            d["hint"] = self.hint
        return d

    def format_text(self) -> str:
        location = self.file or "<project>"
        if self.line:
            location += f":{self.line}:{self.col}"
        line = f"{location}  {self.rule_id} ({self.severity})\n  {self.message}"
        if self.hint:
            line += f"\n  {self.hint}"
        return line


@dataclass
class LintConfig:
    """Agentlint configuration, loaded from pyproject.toml or .agentlint.toml."""

    package: str = ""
    facade_class: str = ""
    core_dir: str = "core"
    interface_files: list[str] = field(
        default_factory=lambda: ["mcp_server.py", "mcp_proxy.py", "middleware.py", "__main__.py"]
    )
    core_allowed_imports: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    select: list[str] = field(default_factory=list)

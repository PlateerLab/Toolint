"""Output formatters for lint results."""

from __future__ import annotations

import json

from agentlint.core.models import LintResult, Severity


def format_text(results: list[LintResult]) -> str:
    """Format results as human-readable text."""
    if not results:
        return "No issues found."

    lines: list[str] = []
    for r in results:
        lines.append(r.format_text())
    lines.append("")

    errors = sum(1 for r in results if r.severity == Severity.ERROR)
    warnings = sum(1 for r in results if r.severity == Severity.WARNING)

    parts: list[str] = []
    if errors:
        parts.append(f"{errors} error{'s' if errors != 1 else ''}")
    if warnings:
        parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")
    summary = ", ".join(parts)
    lines.append(f"{len(results)} issue{'s' if len(results) != 1 else ''} found ({summary})")

    return "\n".join(lines)


def format_json(results: list[LintResult]) -> str:
    """Format results as JSON."""
    errors = sum(1 for r in results if r.severity == Severity.ERROR)
    warnings = sum(1 for r in results if r.severity == Severity.WARNING)
    output = {
        "total": len(results),
        "errors": errors,
        "warnings": warnings,
        "issues": [r.to_dict() for r in results],
    }
    return json.dumps(output, indent=2, ensure_ascii=False)

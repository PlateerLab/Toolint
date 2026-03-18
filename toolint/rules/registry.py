"""Global rule registry — rules register themselves on import."""

from __future__ import annotations

from collections.abc import Callable

from toolint.core.context import ProjectContext
from toolint.core.models import LintResult, RuleDefinition, Severity

RuleChecker = Callable[[ProjectContext], list[LintResult]]

_REGISTRY: list[tuple[str, RuleDefinition, RuleChecker]] = []


def register(
    rule_id: str,
    *,
    name: str,
    description: str,
    severity: Severity,
    layer: str,
) -> Callable[[RuleChecker], RuleChecker]:
    """Decorator to register a rule checker into the global registry."""

    def decorator(fn: RuleChecker) -> RuleChecker:
        if any(r[0] == rule_id for r in _REGISTRY):
            msg = f"Rule {rule_id} already registered"
            raise ValueError(msg)
        rule_def = RuleDefinition(
            id=rule_id,
            name=name,
            description=description,
            severity=severity,
            layer=layer,
        )
        _REGISTRY.append((rule_id, rule_def, fn))
        return fn

    return decorator


def get_all() -> list[tuple[str, RuleDefinition, RuleChecker]]:
    """Return all registered rules."""
    from toolint.rules import (  # noqa: F401
        dependency,
        layer_separation,
        pyproject_rules,
        schema_quality,
        structure,
    )

    return list(_REGISTRY)

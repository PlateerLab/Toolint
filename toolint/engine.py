"""LintEngine — facade that loads rules from the registry and runs checks."""

from __future__ import annotations

from pathlib import Path

from toolint.core.config import load_config
from toolint.core.context import ProjectContext
from toolint.core.models import LintResult, RuleDefinition, Severity


class LintEngine:
    """Main facade: loads rules, runs checks, collects results."""

    def __init__(self) -> None:
        self._rules: dict[str, RuleDefinition] = {}
        self._checkers: dict[str, object] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load all rules from the global registry (once)."""
        if self._loaded:
            return
        from toolint.rules.registry import get_all

        for rule_id, rule_def, checker in get_all():
            self._rules[rule_id] = rule_def
            self._checkers[rule_id] = checker
        self._loaded = True

    def register(
        self,
        rule_id: str,
        *,
        name: str,
        description: str,
        severity: Severity,
        layer: str,
        checker: object,
    ) -> None:
        """Register a single rule manually (skips auto-loading from registry)."""
        self._loaded = True  # prevent auto-loading when using manual registration
        self._rules[rule_id] = RuleDefinition(
            id=rule_id,
            name=name,
            description=description,
            severity=severity,
            layer=layer,
        )
        self._checkers[rule_id] = checker

    @property
    def rules(self) -> dict[str, RuleDefinition]:
        """All registered rules."""
        self._ensure_loaded()
        return dict(self._rules)

    def check(
        self,
        project_dir: str | Path,
        *,
        select: list[str] | None = None,
        ignore: list[str] | None = None,
    ) -> list[LintResult]:
        """Run all applicable rules against a project directory."""
        self._ensure_loaded()

        project_path = Path(project_dir).resolve()
        config, pyproject = load_config(project_path)
        ctx = ProjectContext(project_path, config, pyproject)

        # Determine which rules to run
        effective_select = select or config.select
        effective_ignore = set(ignore or []) | set(config.ignore)

        rule_ids = list(self._checkers.keys())
        if effective_select:
            rule_ids = [r for r in rule_ids if r in effective_select]
        rule_ids = [r for r in rule_ids if r not in effective_ignore]

        # Run checkers
        results: list[LintResult] = []
        for rule_id in sorted(rule_ids):
            checker = self._checkers[rule_id]
            try:
                issues = checker(ctx)
                results.extend(issues)
            except Exception as exc:
                results.append(
                    LintResult(
                        rule_id=rule_id,
                        severity=Severity.WARNING,
                        message=f"Rule {rule_id} crashed: {exc}",
                    )
                )

        return results

    @staticmethod
    def check_summary(results: list[LintResult]) -> dict[str, int]:
        """Return error/warning counts from results."""
        errors = sum(1 for r in results if r.severity == Severity.ERROR)
        warnings = sum(1 for r in results if r.severity == Severity.WARNING)
        return {"total": len(results), "errors": errors, "warnings": warnings}

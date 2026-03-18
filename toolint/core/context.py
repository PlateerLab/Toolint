"""ProjectContext — shared state passed to all rule checkers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from toolint.core.models import LintConfig


class ProjectContext:
    """Pre-computed project state shared across all rule checkers.

    Avoids each rule re-computing pkg_dir, interface files, etc.
    """

    def __init__(
        self,
        project_dir: Path,
        config: LintConfig,
        pyproject: dict[str, Any],
    ) -> None:
        self.project_dir = project_dir
        self.config = config
        self.pyproject = pyproject

    @property
    def pkg_dir(self) -> Path:
        """Package directory path."""
        return self.project_dir / self.config.package

    @property
    def core_dir(self) -> Path:
        """Core directory path."""
        return self.pkg_dir / self.config.core_dir

    @property
    def init_file(self) -> Path:
        """__init__.py path."""
        return self.pkg_dir / "__init__.py"

    @property
    def main_file(self) -> Path:
        """__main__.py path."""
        return self.pkg_dir / "__main__.py"

    def rel_path(self, path: Path) -> str:
        """Get path relative to project_dir as string."""
        return str(path.relative_to(self.project_dir))

    def interface_files(self) -> list[Path]:
        """Get existing interface file paths."""
        return [
            self.pkg_dir / name
            for name in self.config.interface_files
            if (self.pkg_dir / name).exists()
        ]

"""Tests for P0 rules (ATL001-004, ATL101-105, ATL301-303)."""

from __future__ import annotations

from pathlib import Path

from agentlint.core.config import load_config
from agentlint.core.models import LintConfig
from agentlint.rules import dependency, pyproject_rules, structure


def _make_project(tmp_path: Path, pkg: str = "my_tool", files: dict[str, str] | None = None):
    """Create a minimal project structure for testing."""
    pyproject = tmp_path / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            f'[tool.poetry]\nname = "{pkg.replace("_", "-")}"\nversion = "0.1.0"\n'
            f'packages = [{{include = "{pkg}"}}]\n\n'
            f'[tool.poetry.dependencies]\npython = "^3.10"\n\n'
            f'[tool.poetry.scripts]\n{pkg.replace("_", "-")} = "{pkg}.__main__:main"\n'
        )

    pkg_dir = tmp_path / pkg
    pkg_dir.mkdir(exist_ok=True)
    (pkg_dir / "__init__.py").write_text('__version__ = "0.1.0"\n__all__ = ["MyTool"]\n')
    (pkg_dir / "__main__.py").write_text("def main(): pass\n")

    core_dir = pkg_dir / "core"
    core_dir.mkdir(exist_ok=True)
    (core_dir / "__init__.py").write_text("")

    if files:
        for name, content in files.items():
            path = pkg_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    return tmp_path


def _config(**kwargs) -> LintConfig:
    kwargs.setdefault("package", "my_tool")
    return LintConfig(**kwargs)


def _pyproject(tmp_path: Path) -> dict:
    _, pyproject = load_config(tmp_path)
    return pyproject


# === ATL001: facade-exists ===


class TestATL001:
    def test_pass_with_facade_class(self, tmp_path: Path):
        _make_project(
            tmp_path,
            files={
                "facade.py": (
                    "class MyTool:\n"
                    "    def a(self): ...\n"
                    "    def b(self): ...\n"
                    "    def c(self): ...\n"
                )
            },
        )
        cfg = _config(facade_class="MyTool")
        results = structure.check_facade_exists(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_no_package(self, tmp_path: Path):
        cfg = _config(package="nonexistent")
        results = structure.check_facade_exists(tmp_path, cfg, {})
        assert len(results) == 1
        assert results[0].rule_id == "ATL001"

    def test_fail_configured_class_missing(self, tmp_path: Path):
        _make_project(tmp_path)
        cfg = _config(facade_class="DoesNotExist")
        results = structure.check_facade_exists(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1

    def test_auto_detect_facade(self, tmp_path: Path):
        _make_project(
            tmp_path,
            files={
                "engine.py": (
                    "class Engine:\n"
                    "    def search(self): ...\n"
                    "    def ingest(self): ...\n"
                    "    def retrieve(self): ...\n"
                )
            },
        )
        cfg = _config()  # no facade_class set
        results = structure.check_facade_exists(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0


# === ATL002: __main__.py exists ===


class TestATL002:
    def test_pass(self, tmp_path: Path):
        _make_project(tmp_path)
        cfg = _config()
        results = structure.check_main_module(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail(self, tmp_path: Path):
        _make_project(tmp_path)
        (tmp_path / "my_tool" / "__main__.py").unlink()
        cfg = _config()
        results = structure.check_main_module(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert results[0].rule_id == "ATL002"


# === ATL003: __all__ ===


class TestATL003:
    def test_pass(self, tmp_path: Path):
        _make_project(tmp_path)
        cfg = _config(facade_class="MyTool")
        results = structure.check_init_all(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_no_all(self, tmp_path: Path):
        _make_project(tmp_path)
        (tmp_path / "my_tool" / "__init__.py").write_text('__version__ = "0.1.0"\n')
        cfg = _config()
        results = structure.check_init_all(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert results[0].rule_id == "ATL003"

    def test_fail_facade_not_in_all(self, tmp_path: Path):
        _make_project(tmp_path)
        (tmp_path / "my_tool" / "__init__.py").write_text(
            '__version__ = "0.1.0"\n__all__ = ["OtherClass"]\n'
        )
        cfg = _config(facade_class="MyTool")
        results = structure.check_init_all(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1


# === ATL004: version match ===


class TestATL004:
    def test_pass(self, tmp_path: Path):
        _make_project(tmp_path)
        cfg = _config()
        results = structure.check_version_match(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_mismatch(self, tmp_path: Path):
        _make_project(tmp_path)
        (tmp_path / "my_tool" / "__init__.py").write_text('__version__ = "0.2.0"\n__all__ = []\n')
        cfg = _config()
        results = structure.check_version_match(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert "mismatch" in results[0].message.lower()

    def test_fail_no_version(self, tmp_path: Path):
        _make_project(tmp_path)
        (tmp_path / "my_tool" / "__init__.py").write_text("__all__ = []\n")
        cfg = _config()
        results = structure.check_version_match(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert results[0].rule_id == "ATL004"


# === ATL101: core stdlib only ===


class TestATL101:
    def test_pass_stdlib(self, tmp_path: Path):
        _make_project(
            tmp_path, files={"core/engine.py": "import json\nimport os\nfrom pathlib import Path\n"}
        )
        cfg = _config()
        results = dependency.check_core_stdlib_only(tmp_path, cfg, {})
        assert len(results) == 0

    def test_fail_third_party(self, tmp_path: Path):
        _make_project(tmp_path, files={"core/engine.py": "import numpy\n"})
        cfg = _config()
        results = dependency.check_core_stdlib_only(tmp_path, cfg, {})
        assert len(results) == 1
        assert results[0].rule_id == "ATL101"
        assert "numpy" in results[0].message

    def test_pass_internal(self, tmp_path: Path):
        _make_project(tmp_path, files={"core/engine.py": "from my_tool.core.models import Foo\n"})
        cfg = _config()
        results = dependency.check_core_stdlib_only(tmp_path, cfg, {})
        assert len(results) == 0

    def test_pass_allowed(self, tmp_path: Path):
        _make_project(tmp_path, files={"core/engine.py": "import numpy\n"})
        cfg = _config(core_allowed_imports=["numpy"])
        results = dependency.check_core_stdlib_only(tmp_path, cfg, {})
        assert len(results) == 0

    def test_guarded_still_fails(self, tmp_path: Path):
        """Even with try/except, core should not import third-party."""
        _make_project(
            tmp_path,
            files={
                "core/engine.py": "try:\n    import numpy\nexcept ImportError:\n    numpy = None\n"
            },
        )
        cfg = _config()
        results = dependency.check_core_stdlib_only(tmp_path, cfg, {})
        assert len(results) == 1  # core is strict: no third-party at all


# === ATL102: optional import guard ===


class TestATL102:
    def test_pass_guarded(self, tmp_path: Path):
        _make_project(
            tmp_path,
            files={"feature.py": "try:\n    import numpy\nexcept ImportError:\n    numpy = None\n"},
        )
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.10"\n\n'
            '[tool.poetry.extras]\nml = ["numpy"]\n'
        )
        cfg = _config()
        results = dependency.check_optional_import_guard(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_unguarded(self, tmp_path: Path):
        _make_project(tmp_path, files={"feature.py": "import numpy\n"})
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.10"\n\n'
            '[tool.poetry.extras]\nml = ["numpy"]\n'
        )
        cfg = _config()
        results = dependency.check_optional_import_guard(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert results[0].rule_id == "ATL102"

    def test_pass_lazy_import(self, tmp_path: Path):
        """Import inside a function is allowed (lazy import pattern)."""
        _make_project(
            tmp_path,
            files={
                "feature.py": "def do_stuff():\n    import numpy\n    return numpy.array([1])\n"
            },
        )
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.10"\n\n'
            '[tool.poetry.extras]\nml = ["numpy"]\n'
        )
        cfg = _config()
        results = dependency.check_optional_import_guard(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0


# === ATL104: extras registered ===


class TestATL104:
    def test_pass(self, tmp_path: Path):
        _make_project(
            tmp_path,
            files={"feature.py": "try:\n    import numpy\nexcept ImportError:\n    numpy = None\n"},
        )
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.10"\n\n'
            '[tool.poetry.extras]\nml = ["numpy"]\n'
        )
        cfg = _config()
        results = dependency.check_extras_registered(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_unregistered(self, tmp_path: Path):
        _make_project(
            tmp_path,
            files={"feature.py": "try:\n    import scipy\nexcept ImportError:\n    scipy = None\n"},
        )
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.10"\n'
        )
        cfg = _config()
        results = dependency.check_extras_registered(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert "scipy" in results[0].message


# === ATL103: import guard hint ===


class TestATL103:
    def _pyproject_with_extras(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.10"\n\n'
            '[tool.poetry.extras]\nml = ["numpy"]\nviz = ["pyvis"]\n'
        )

    def test_skip_graceful_none(self, tmp_path: Path):
        """Graceful fallback (= None) should NOT trigger ATL103."""
        _make_project(
            tmp_path,
            files={
                "feature.py": ("try:\n    import numpy as np\nexcept ImportError:\n    np = None\n")
            },
        )
        self._pyproject_with_extras(tmp_path)
        cfg = _config()
        results = dependency.check_import_guard_hint(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_skip_graceful_return(self, tmp_path: Path):
        """Graceful fallback (return) should NOT trigger ATL103."""
        _make_project(
            tmp_path,
            files={
                "feature.py": (
                    "def maybe_use_numpy():\n"
                    "    try:\n        import numpy\n"
                    "    except ImportError:\n        return\n"
                )
            },
        )
        self._pyproject_with_extras(tmp_path)
        cfg = _config()
        results = dependency.check_import_guard_hint(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_skip_graceful_false(self, tmp_path: Path):
        """Graceful fallback (= False) should NOT trigger ATL103."""
        _make_project(
            tmp_path,
            files={
                "feature.py": (
                    "try:\n    import numpy\n    _HAS = True\n"
                    "except ImportError:\n    _HAS = False\n"
                )
            },
        )
        self._pyproject_with_extras(tmp_path)
        cfg = _config()
        results = dependency.check_import_guard_hint(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_require_function_counts_as_hint(self, tmp_path: Path):
        """_require_xxx() with install message should NOT trigger ATL103."""
        _make_project(
            tmp_path,
            files={
                "feature.py": (
                    "try:\n    from pyvis.network import Network\n"
                    "except ImportError:\n    Network = None\n\n"
                    "def _require_pyvis():\n"
                    "    if Network is None:\n"
                    '        raise ImportError("pip install pyvis")\n'
                )
            },
        )
        self._pyproject_with_extras(tmp_path)
        cfg = _config()
        results = dependency.check_import_guard_hint(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_raise_without_hint(self, tmp_path: Path):
        """except block that raises without install hint SHOULD trigger ATL103."""
        _make_project(
            tmp_path,
            files={
                "feature.py": (
                    "try:\n    import numpy\n"
                    "except ImportError:\n"
                    '    raise RuntimeError("numpy not available")\n'
                )
            },
        )
        self._pyproject_with_extras(tmp_path)
        cfg = _config()
        results = dependency.check_import_guard_hint(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1


class TestATL104Extra:
    def test_pyyaml_yaml_mapping(self, tmp_path: Path):
        """pyyaml in extras should match 'import yaml' (no false positive)."""
        _make_project(
            tmp_path,
            files={"feature.py": ("try:\n    import yaml\nexcept ImportError:\n    yaml = None\n")},
        )
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.10"\n\n'
            '[tool.poetry.extras]\nopenapi = ["pyyaml"]\n'
        )
        cfg = _config()
        results = dependency.check_extras_registered(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_lazy_import_skipped(self, tmp_path: Path):
        """Lazy import (inside function) should NOT trigger ATL104."""
        _make_project(
            tmp_path,
            files={
                "feature.py": (
                    "def use_litellm():\n"
                    "    try:\n        import litellm\n"
                    "    except ImportError:\n"
                    '        raise ImportError("install litellm")\n'
                    "    return litellm.completion()\n"
                )
            },
        )
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.10"\n'
        )
        cfg = _config()
        results = dependency.check_extras_registered(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0


# === ATL301: scripts entry ===


class TestATL301:
    def test_pass(self, tmp_path: Path):
        _make_project(tmp_path)
        cfg = _config()
        results = pyproject_rules.check_scripts_entry(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_no_scripts(self, tmp_path: Path):
        _make_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n'
        )
        cfg = _config()
        results = pyproject_rules.check_scripts_entry(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert results[0].rule_id == "ATL301"


# === ATL302: mcp extras ===


class TestATL302:
    def test_pass_no_mcp(self, tmp_path: Path):
        _make_project(tmp_path)
        cfg = _config()
        results = pyproject_rules.check_mcp_extras(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_mcp_no_extras(self, tmp_path: Path):
        _make_project(tmp_path, files={"mcp_server.py": "# MCP server\n"})
        cfg = _config()
        results = pyproject_rules.check_mcp_extras(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert results[0].rule_id == "ATL302"

    def test_pass_mcp_with_extras(self, tmp_path: Path):
        _make_project(tmp_path, files={"mcp_server.py": "# MCP server\n"})
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.scripts]\nmy-tool = "my_tool.__main__:main"\n\n'
            '[tool.poetry.extras]\nmcp = ["mcp"]\n'
        )
        cfg = _config()
        results = pyproject_rules.check_mcp_extras(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0


# === ATL303: all extras complete ===


class TestATL303:
    def test_pass(self, tmp_path: Path):
        _make_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.scripts]\nmy-tool = "my_tool.__main__:main"\n\n'
            '[tool.poetry.extras]\nmcp = ["mcp"]\nml = ["numpy"]\n'
            'all = ["mcp", "numpy"]\n'
        )
        cfg = _config()
        results = pyproject_rules.check_all_extras_complete(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

    def test_fail_missing(self, tmp_path: Path):
        _make_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "my-tool"\nversion = "0.1.0"\n'
            'packages = [{include = "my_tool"}]\n\n'
            '[tool.poetry.scripts]\nmy-tool = "my_tool.__main__:main"\n\n'
            '[tool.poetry.extras]\nmcp = ["mcp"]\nml = ["numpy"]\n'
            'all = ["mcp"]\n'  # missing numpy
        )
        cfg = _config()
        results = pyproject_rules.check_all_extras_complete(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 1
        assert "numpy" in results[0].message

    def test_no_all_group(self, tmp_path: Path):
        """No 'all' extras group is fine — not required."""
        _make_project(tmp_path)
        cfg = _config()
        results = pyproject_rules.check_all_extras_complete(tmp_path, cfg, _pyproject(tmp_path))
        assert len(results) == 0

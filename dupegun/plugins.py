"""
dupegun plugin system
=====================

Lets users register custom "keep" strategies without modifying dupegun's core.

Usage in a plugin file
-----------------------

    # my_plugin.py
    from dupegun.plugins import register_strategy

    @register_strategy("by_name")
    def keep_by_name(paths):
        \"\"\"Keep the file whose name comes first alphabetically.\"\"\"
        return min(paths, key=lambda p: p.name.lower())

Loading plugins
---------------

Plugins are loaded in two ways:

1. Via the config file (~/.dupegun.toml):

    [plugins]
    load = ["my_plugin.py", "/absolute/path/to/other_plugin.py"]

2. Via the CLI:

    dupegun delete ~/Downloads --plugin my_plugin.py --strategy by_name

After loading, the registered strategy name can be used anywhere
--strategy is accepted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable, Dict, List

# Global registry: strategy_name -> callable(paths: list[Path]) -> Path
_REGISTRY: Dict[str, Callable] = {}


def register_strategy(name: str):
    """
    Decorator to register a custom keep-strategy.

    The decorated function must accept a list of Path objects and return
    the single Path that should be kept.

    Example::

        @register_strategy("by_name")
        def keep_alphabetically(paths):
            return min(paths, key=lambda p: p.name.lower())
    """
    def decorator(fn: Callable) -> Callable:
        if not callable(fn):
            raise TypeError(f"register_strategy: '{name}' must be callable")
        _REGISTRY[name] = fn
        return fn
    return decorator


def get_strategy(name: str) -> Callable | None:
    """Return the callable for *name*, or None if not registered."""
    return _REGISTRY.get(name)


def list_strategies() -> List[str]:
    """Return all registered custom strategy names."""
    return list(_REGISTRY.keys())


def load_plugin(path: str | Path) -> None:
    """
    Dynamically load a Python file as a plugin module.

    Any @register_strategy decorators in the file are executed on import,
    which populates the registry automatically.

    Args:
        path: Path to the .py plugin file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ImportError:       If the file fails to import.
    """
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Plugin file not found: {p}")

    module_name = f"_dupegun_plugin_{p.stem}"
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin: {p}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


def load_plugins(paths: list) -> None:
    """Load multiple plugin files. Silently skips None/empty entries."""
    for path in paths:
        if path:
            load_plugin(path)
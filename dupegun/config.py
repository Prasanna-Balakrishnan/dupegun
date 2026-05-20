"""
dupegun config file support
============================

Reads ~/.dupegun.toml (or a path you specify with --config) and merges
the settings into CLI defaults.  CLI flags always win over config values.

Example ~/.dupegun.toml
------------------------

    [defaults]
    strategy  = "newest"
    min_size  = "100KB"
    exclude   = ["node_modules", ".git", "Windows"]

    [plugins]
    load = ["~/my_plugin.py"]

Supported keys under [defaults]
---------------------------------
    strategy   str          "shortest" | "newest" | "oldest" | custom name
    min_size   str|int      e.g. "1MB", 1048576
    max_size   str|int      e.g. "500MB"
    exclude    list[str]    folder names to always skip
    types      list[str]    file extensions to always include
    pattern    str          regex pattern
    dry_run    bool         default dry-run state (true = safe)

Supported keys under [plugins]
--------------------------------
    load       list[str]    paths to plugin .py files to auto-load
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Python 3.11+ ships tomllib in the stdlib; older versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib          # type: ignore[no-redef]
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            tomllib = None      # type: ignore[assignment]

DEFAULT_CONFIG_PATH = Path.home() / ".dupegun.toml"


def _load_toml(path: Path) -> Dict[str, Any]:
    """Read and parse a TOML file. Returns {} on missing file or parse error."""
    if tomllib is None:
        return {}
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """
    Load the dupegun config file.

    Args:
        config_path: Explicit path to a .toml file, or None to use the default
                     (~/.dupegun.toml).

    Returns:
        A flat dict of resolved settings ready to merge into CLI defaults.
        Keys match CLI option names: strategy, min_size, max_size, exclude,
        types, pattern, dry_run, plugin_files.
        Returns {} if the config file does not exist.
    """
    path = Path(config_path).expanduser() if config_path else DEFAULT_CONFIG_PATH

    # Missing file → no config at all; return immediately so callers
    # receive a clean empty dict and no defaults bleed through.
    if not path.exists():
        return {}

    raw    = _load_toml(path)
    result: Dict[str, Any] = {}

    defaults = raw.get("defaults", {})
    if isinstance(defaults, dict):
        for key in ("strategy", "min_size", "max_size", "pattern"):
            if key in defaults:
                result[key] = defaults[key]
        for key in ("exclude", "types"):
            if key in defaults and isinstance(defaults[key], list):
                result[key] = tuple(defaults[key])
        if "dry_run" in defaults:
            result["dry_run"] = bool(defaults["dry_run"])

    plugins_section = raw.get("plugins", {})
    if isinstance(plugins_section, dict):
        plugin_files = plugins_section.get("load", [])
        if isinstance(plugin_files, list) and plugin_files:
            result["plugin_files"] = [
                str(Path(p).expanduser()) for p in plugin_files
            ]

    return result


def config_exists(config_path: str | Path | None = None) -> bool:
    """Return True if the config file exists."""
    path = Path(config_path).expanduser() if config_path else DEFAULT_CONFIG_PATH
    return path.exists()


def generate_default_config() -> str:
    """Return a ready-to-use default ~/.dupegun.toml as a string."""
    return """\
# dupegun configuration file
# Save as ~/.dupegun.toml
#
# All settings here become your defaults.
# CLI flags always override config values.

[defaults]
# Which duplicate to keep: "shortest" | "newest" | "oldest" | custom plugin name
strategy = "shortest"

# Skip files smaller than this (bytes or human-readable: 1KB, 1MB, 1GB)
# min_size = "1"

# Skip files larger than this
# max_size = "500MB"

# Always skip these folder names
# exclude = ["node_modules", ".git", "Windows", "Program Files"]

# Only scan these extensions (leave commented to scan all)
# types = [".jpg", ".png", ".mp4"]

# Only scan filenames matching this regex
# pattern = ""

# Dry-run ON by default (safe). Set false to default to --no-dry-run.
# dry_run = true

[plugins]
# Paths to plugin .py files to load automatically
# load = ["~/my_dupegun_plugin.py"]
"""
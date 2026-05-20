"""
Tests for dupegun v2.0.0 features:
  - Plugin system   (register_strategy, load_plugin)
  - Config file     (load_config, generate_default_config)
  - TUI             (import guard when textual missing)
  - Watch mode      (import guard when watchdog missing)
"""

import os
import sys
import tempfile
from pathlib import Path

# ── plugin system ─────────────────────────────────────────────────────────────

def test_register_strategy_basic():
    """A registered strategy can be retrieved by name."""
    from dupegun.plugins import register_strategy, get_strategy, _REGISTRY

    @register_strategy("test_alpha")
    def keep_alpha(paths):
        return min(paths, key=lambda p: p.name)

    assert get_strategy("test_alpha") is not None
    # Cleanup
    _REGISTRY.pop("test_alpha", None)


def test_register_strategy_is_called():
    """The registered callable is actually invoked by pick_keeper."""
    from dupegun.plugins import register_strategy, _REGISTRY
    from dupegun.actions import pick_keeper

    called_with = []

    @register_strategy("test_spy")
    def spy_strategy(paths):
        called_with.extend(paths)
        return paths[0]

    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        pick_keeper([a, b], "test_spy")

    assert len(called_with) == 2
    _REGISTRY.pop("test_spy", None)


def test_list_strategies():
    """list_strategies returns registered names."""
    from dupegun.plugins import register_strategy, list_strategies, _REGISTRY

    @register_strategy("test_list_me")
    def dummy(paths):
        return paths[0]

    assert "test_list_me" in list_strategies()
    _REGISTRY.pop("test_list_me", None)


def test_get_strategy_unknown_returns_none():
    """get_strategy returns None for an unknown name."""
    from dupegun.plugins import get_strategy
    assert get_strategy("__nonexistent_strategy__") is None


def test_load_plugin_from_file():
    """load_plugin executes a .py file and registers its strategies."""
    from dupegun.plugins import load_plugin, get_strategy, _REGISTRY

    plugin_code = """\
from dupegun.plugins import register_strategy

@register_strategy("file_plugin_strategy")
def keep_last(paths):
    return paths[-1]
"""
    with tempfile.TemporaryDirectory() as tmp:
        plugin_file = Path(tmp) / "my_plugin.py"
        plugin_file.write_text(plugin_code, encoding="utf-8")
        load_plugin(plugin_file)

    assert get_strategy("file_plugin_strategy") is not None
    _REGISTRY.pop("file_plugin_strategy", None)


def test_load_plugin_missing_file():
    """load_plugin raises FileNotFoundError for a missing file."""
    from dupegun.plugins import load_plugin
    import pytest
    with pytest.raises(FileNotFoundError):
        load_plugin("/nonexistent/path/plugin.py")


def test_plugin_strategy_picks_correctly():
    """A plugin strategy that keeps the longest-named file works end-to-end."""
    from dupegun.plugins import register_strategy, _REGISTRY
    from dupegun.actions import pick_keeper

    @register_strategy("test_longest_name")
    def keep_longest(paths):
        return max(paths, key=lambda p: len(p.name))

    with tempfile.TemporaryDirectory() as tmp:
        short = Path(tmp) / "a.txt"
        long_ = Path(tmp) / "very_long_name.txt"
        short.write_bytes(b"data")
        long_.write_bytes(b"data")
        result = pick_keeper([short, long_], "test_longest_name")
        assert result == long_

    _REGISTRY.pop("test_longest_name", None)


# ── config file ───────────────────────────────────────────────────────────────

def test_generate_default_config_is_string():
    """generate_default_config returns a non-empty string."""
    from dupegun.config import generate_default_config
    cfg = generate_default_config()
    assert isinstance(cfg, str)
    assert len(cfg) > 0


def test_generate_default_config_has_sections():
    """The default config template has [defaults] and [plugins] sections."""
    from dupegun.config import generate_default_config
    cfg = generate_default_config()
    assert "[defaults]" in cfg
    assert "[plugins]" in cfg


def test_load_config_missing_file_returns_empty():
    """load_config returns {} when the config file doesn't exist."""
    from dupegun.config import load_config
    result = load_config("/nonexistent/path/.dupegun.toml")
    assert result == {}


def test_load_config_reads_strategy(tmp_path):
    """load_config reads the strategy key from [defaults]."""
    from dupegun.config import load_config
    cfg_file = tmp_path / "test.toml"
    cfg_file.write_text('[defaults]\nstrategy = "newest"\n', encoding="utf-8")
    result = load_config(cfg_file)
    assert result.get("strategy") == "newest"


def test_load_config_reads_exclude_list(tmp_path):
    """load_config reads the exclude list from [defaults]."""
    from dupegun.config import load_config
    cfg_file = tmp_path / "test.toml"
    cfg_file.write_text(
        '[defaults]\nexclude = ["node_modules", ".git"]\n', encoding="utf-8"
    )
    result = load_config(cfg_file)
    assert "node_modules" in result.get("exclude", ())
    assert ".git" in result.get("exclude", ())


def test_load_config_reads_min_size(tmp_path):
    """load_config reads min_size from [defaults]."""
    from dupegun.config import load_config
    cfg_file = tmp_path / "test.toml"
    cfg_file.write_text('[defaults]\nmin_size = "1MB"\n', encoding="utf-8")
    result = load_config(cfg_file)
    assert result.get("min_size") == "1MB"


def test_load_config_reads_plugin_files(tmp_path):
    """load_config reads plugin paths from [plugins]."""
    from dupegun.config import load_config
    cfg_file = tmp_path / "test.toml"
    cfg_file.write_text(
        '[plugins]\nload = ["~/my_plugin.py"]\n', encoding="utf-8"
    )
    result = load_config(cfg_file)
    assert "plugin_files" in result
    assert len(result["plugin_files"]) == 1


def test_config_exists_false_for_missing(tmp_path):
    """config_exists returns False when the file doesn't exist."""
    from dupegun.config import config_exists
    assert not config_exists(tmp_path / "nonexistent.toml")


def test_config_exists_true_when_present(tmp_path):
    """config_exists returns True when the file exists."""
    from dupegun.config import config_exists
    f = tmp_path / "dupegun.toml"
    f.write_text("[defaults]\n", encoding="utf-8")
    assert config_exists(f)


# ── TUI import guard ──────────────────────────────────────────────────────────

def test_tui_raises_without_textual(monkeypatch):
    """run_tui raises SystemExit with a helpful message if textual is missing."""
    import dupegun.tui as tui_module
    monkeypatch.setattr(tui_module, "_TEXTUAL_AVAILABLE", False)

    import pytest
    with pytest.raises(SystemExit, match="textual"):
        tui_module.run_tui({})


# ── Watch import guard ────────────────────────────────────────────────────────

def test_watch_raises_without_watchdog(monkeypatch):
    """run_watch raises SystemExit with a helpful message if watchdog is missing."""
    import dupegun.watcher as watcher_module
    monkeypatch.setattr(watcher_module, "_WATCHDOG_AVAILABLE", False)

    import pytest
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(SystemExit, match="watchdog"):
            watcher_module.run_watch(Path(tmp))
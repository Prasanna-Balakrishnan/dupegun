"""
Tests for dupegun v1.3.0 features:
  - HTML report  (--html)
  - Log file     (--log)
  - Stats command (dupegun stats)
"""

import os
import time
import tempfile
from pathlib import Path

from dupegun.scanner import find_duplicates, walk_files
from dupegun.reporter import export_html, print_stats
from dupegun.actions import delete_dupes

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_dupes(tmp, content=b"duplicate content"):
    a = Path(tmp) / "a.txt"
    b = Path(tmp) / "b.txt"
    a.write_bytes(content)
    b.write_bytes(content)
    return find_duplicates([Path(tmp)])

# ── HTML report ───────────────────────────────────────────────────────────────

def test_export_html_creates_file():
    """export_html creates a file at the given path."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        out = Path(tmp) / "report.html"
        export_html(groups, str(out))
        assert out.exists()

def test_export_html_is_valid_html():
    """The output starts with a DOCTYPE and contains basic HTML structure."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        out = Path(tmp) / "report.html"
        export_html(groups, str(out))
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content

def test_export_html_contains_group_info():
    """The HTML report includes group headings and file paths."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        out = Path(tmp) / "report.html"
        export_html(groups, str(out))
        content = out.read_text(encoding="utf-8")
        assert "Group 1" in content
        assert "a.txt" in content
        assert "b.txt" in content

def test_export_html_shows_wasted_space():
    """The HTML summary cards display wasted space."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        out = Path(tmp) / "report.html"
        export_html(groups, str(out))
        content = out.read_text(encoding="utf-8")
        assert "Wasted space" in content

def test_export_html_empty_groups():
    """export_html handles an empty groups dict without crashing."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "empty_report.html"
        export_html({}, str(out))
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

def test_export_html_multiple_groups():
    """HTML report correctly shows multiple groups."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.txt").write_bytes(b"content one")
        Path(tmp, "b.txt").write_bytes(b"content one")
        Path(tmp, "c.jpg").write_bytes(b"content two")
        Path(tmp, "d.jpg").write_bytes(b"content two")
        groups = find_duplicates([Path(tmp)])
        out = Path(tmp) / "report.html"
        export_html(groups, str(out))
        content = out.read_text(encoding="utf-8")
        assert "Group 1" in content
        assert "Group 2" in content

# ── log file ──────────────────────────────────────────────────────────────────

def test_log_file_created_after_delete():
    """A log file is created when --log is passed and files are deleted."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        log = Path(tmp) / "deleted.log"
        delete_dupes(groups, strategy="shortest", dry_run=False, log_path=str(log))
        assert log.exists()

def test_log_file_contains_deleted_path():
    """The log records the path of the deleted file."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        log = Path(tmp) / "deleted.log"
        delete_dupes(groups, strategy="shortest", dry_run=False, log_path=str(log))
        content = log.read_text(encoding="utf-8")
        assert "deleted" in content
        assert ".txt" in content

def test_log_file_contains_kept_path():
    """The log records which file was kept."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        log = Path(tmp) / "deleted.log"
        delete_dupes(groups, strategy="shortest", dry_run=False, log_path=str(log))
        content = log.read_text(encoding="utf-8")
        assert "kept=" in content

def test_log_file_tsv_format():
    """Each log line has tab-separated fields."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        log = Path(tmp) / "deleted.log"
        delete_dupes(groups, strategy="shortest", dry_run=False, log_path=str(log))
        lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) >= 1
        # Each line should have at least 4 tab-separated fields
        for line in lines:
            parts = line.split("\t")
            assert len(parts) >= 4

def test_log_not_created_on_dry_run():
    """No log file is written when dry_run=True."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        log = Path(tmp) / "deleted.log"
        delete_dupes(groups, strategy="shortest", dry_run=True, log_path=str(log))
        assert not log.exists()

def test_log_appends_on_multiple_runs():
    """Calling delete_dupes twice appends to the same log file."""
    with tempfile.TemporaryDirectory() as tmp:
        # First batch
        a1 = Path(tmp) / "a1.txt"
        b1 = Path(tmp) / "b1.txt"
        a1.write_bytes(b"batch one")
        b1.write_bytes(b"batch one")
        groups1 = find_duplicates([Path(tmp)])
        log = Path(tmp) / "deleted.log"
        delete_dupes(groups1, strategy="shortest", dry_run=False, log_path=str(log))
        lines_after_first = log.read_text(encoding="utf-8").splitlines()

        # Second batch
        a2 = Path(tmp) / "a2.bin"
        b2 = Path(tmp) / "b2.bin"
        a2.write_bytes(b"batch two content")
        b2.write_bytes(b"batch two content")
        groups2 = find_duplicates([Path(tmp)])
        delete_dupes(groups2, strategy="shortest", dry_run=False, log_path=str(log))
        lines_after_second = log.read_text(encoding="utf-8").splitlines()

        assert len(lines_after_second) > len(lines_after_first)

# ── stats command ─────────────────────────────────────────────────────────────

def test_print_stats_does_not_crash():
    """print_stats runs without error on a normal folder."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.txt").write_bytes(b"hello")
        Path(tmp, "b.txt").write_bytes(b"hello")
        Path(tmp, "c.txt").write_bytes(b"unique")
        roots     = [Path(tmp)]
        all_files = list(walk_files(Path(tmp)))
        groups    = find_duplicates(roots)
        print_stats(roots, groups, all_files)   # should not raise

def test_print_stats_empty_folder():
    """print_stats handles an empty folder gracefully."""
    with tempfile.TemporaryDirectory() as tmp:
        roots     = [Path(tmp)]
        all_files = []
        groups    = {}
        print_stats(roots, groups, all_files)

def test_stats_total_files_count():
    """all_files fed to print_stats matches actual file count."""
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(5):
            Path(tmp, f"file{i}.txt").write_bytes(b"x" * (i + 1))
        all_files = list(walk_files(Path(tmp)))
        assert len(all_files) == 5

def test_stats_wasted_calculation():
    """Wasted space in stats equals size × (copies - 1) for each group."""
    from dupegun.reporter import _wasted
    with tempfile.TemporaryDirectory() as tmp:
        content = b"y" * 1000
        Path(tmp, "a.bin").write_bytes(content)
        Path(tmp, "b.bin").write_bytes(content)
        Path(tmp, "c.bin").write_bytes(content)
        groups = find_duplicates([Path(tmp)])
        # 3 copies of 1000 bytes → 2000 bytes wasted
        assert _wasted(groups) == 2000
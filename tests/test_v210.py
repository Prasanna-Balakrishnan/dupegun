"""
Tests for dupegun v2.1.0 features:
  - restore command
  - dry-run summary (print_dry_run_summary)
  - ETA progress bar (TimeRemainingColumn in _scan)
  - colorized --count with bar (print_count)
"""

import os
import time
import tempfile
from pathlib import Path

from dupegun.scanner import find_duplicates
from dupegun.reporter import print_count, print_dry_run_summary
from dupegun.actions import delete_dupes
from dupegun.restore import restore_from_log, _parse_log

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_dupes(tmp, content=b"duplicate content"):
    a = Path(tmp) / "a.txt"
    b = Path(tmp) / "b.txt"
    a.write_bytes(content)
    b.write_bytes(content)
    return find_duplicates([Path(tmp)])


def _make_log_with_deletion(tmp) -> tuple[Path, Path, Path]:
    """Create a duplicate, delete it with a log, return (log, keeper, deleted)."""
    a = Path(tmp) / "keeper.txt"
    b = Path(tmp) / "deleted.txt"
    a.write_bytes(b"restore test content")
    b.write_bytes(b"restore test content")
    groups = find_duplicates([Path(tmp)])
    log = Path(tmp) / "test.log"
    delete_dupes(groups, strategy="shortest", dry_run=False, log_path=str(log))
    # keeper is the shortest path; figure out which was deleted
    keeper  = min([a, b], key=lambda p: len(str(p)))
    deleted = max([a, b], key=lambda p: len(str(p)))
    return log, keeper, deleted

# ── restore: log parsing ──────────────────────────────────────────────────────

def test_parse_log_reads_entries():
    """_parse_log correctly parses a well-formed log file."""
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "test.log"
        log.write_text(
            "2026-01-01 10:00:00\tdeleted\tkept=/a/keeper.txt\t"
            "deleted=/a/copy.txt\tsize=1024\n",
            encoding="utf-8",
        )
        entries = _parse_log(str(log))
        assert len(entries) == 1
        assert entries[0]["action"] == "deleted"
        assert entries[0]["kept"] == "/a/keeper.txt"
        assert entries[0]["deleted"] == "/a/copy.txt"
        assert entries[0]["size_bytes"] == 1024


def test_parse_log_skips_malformed_lines():
    """_parse_log silently skips lines that don't have enough fields."""
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "test.log"
        log.write_text(
            "bad line\n"
            "2026-01-01 10:00:00\tdeleted\tkept=/a.txt\tdeleted=/b.txt\tsize=100\n",
            encoding="utf-8",
        )
        entries = _parse_log(str(log))
        assert len(entries) == 1


def test_parse_log_missing_file():
    """_parse_log raises FileNotFoundError for missing log."""
    import pytest
    with pytest.raises(FileNotFoundError):
        _parse_log("/nonexistent/path/deleted.log")


def test_parse_log_empty_file():
    """_parse_log returns [] for an empty log file."""
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "empty.log"
        log.write_text("", encoding="utf-8")
        assert _parse_log(str(log)) == []

# ── restore: dry run ──────────────────────────────────────────────────────────

def test_restore_dry_run_does_not_create_files():
    """restore_from_log with dry_run=True does not restore any files."""
    with tempfile.TemporaryDirectory() as tmp:
        log, keeper, deleted = _make_log_with_deletion(tmp)
        assert not deleted.exists()
        restore_from_log(str(log), dry_run=True)
        assert not deleted.exists()  # still gone after dry run


def test_restore_dry_run_no_crash_on_empty_log():
    """restore_from_log handles an empty log gracefully."""
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "empty.log"
        log.write_text("", encoding="utf-8")
        restore_from_log(str(log), dry_run=True)  # should not raise

# ── restore: actual restore ───────────────────────────────────────────────────

def test_restore_recreates_deleted_file():
    """restore_from_log --no-dry-run copies the keeper to the deleted path."""
    with tempfile.TemporaryDirectory() as tmp:
        log, keeper, deleted = _make_log_with_deletion(tmp)
        assert keeper.exists()
        assert not deleted.exists()

        restore_from_log(str(log), dry_run=False)

        assert deleted.exists(), "Deleted file should be restored"
        assert keeper.exists(),  "Keeper should still exist"


def test_restore_file_content_matches():
    """The restored file has the same content as the keeper."""
    with tempfile.TemporaryDirectory() as tmp:
        log, keeper, deleted = _make_log_with_deletion(tmp)
        restore_from_log(str(log), dry_run=False)
        assert deleted.read_bytes() == keeper.read_bytes()


def test_restore_skips_if_dest_already_exists():
    """If the destination already exists, restore skips it without error."""
    with tempfile.TemporaryDirectory() as tmp:
        log, keeper, deleted = _make_log_with_deletion(tmp)
        # Re-create the deleted path manually
        deleted.write_bytes(b"already here")
        restore_from_log(str(log), dry_run=False)  # should not raise or overwrite
        assert deleted.read_bytes() == b"already here"


def test_restore_skips_if_keeper_missing():
    """If the keeper is gone, restore skips that entry without crashing."""
    with tempfile.TemporaryDirectory() as tmp:
        log, keeper, deleted = _make_log_with_deletion(tmp)
        keeper.unlink()  # remove the keeper too
        restore_from_log(str(log), dry_run=False)  # should not raise

# ── dry-run summary ───────────────────────────────────────────────────────────

def test_print_dry_run_summary_does_not_crash():
    """print_dry_run_summary runs without error."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        print_dry_run_summary(groups, strategy="shortest")


def test_print_dry_run_summary_empty_groups():
    """print_dry_run_summary handles empty groups gracefully."""
    print_dry_run_summary({}, strategy="shortest")


def test_dry_run_does_not_delete():
    """Running delete with dry_run=True leaves all files intact."""
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        a.write_bytes(b"same content")
        b.write_bytes(b"same content")
        groups = find_duplicates([Path(tmp)])
        delete_dupes(groups, strategy="shortest", dry_run=True)
        assert a.exists() and b.exists()

# ── colorized count ───────────────────────────────────────────────────────────

def test_print_count_no_crash():
    """print_count runs without error with and without total_size."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        print_count(groups)                         # no total_size
        print_count(groups, total_size=10_000)      # with total_size


def test_print_count_zero_total_size():
    """print_count handles total_size=0 without division error."""
    with tempfile.TemporaryDirectory() as tmp:
        groups = _make_dupes(tmp)
        print_count(groups, total_size=0)


def test_print_count_empty_groups():
    """print_count handles empty groups dict without crashing."""
    print_count({}, total_size=0)

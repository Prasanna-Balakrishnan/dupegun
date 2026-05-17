import os
import tempfile
from pathlib import Path
from dupegun.scanner import find_duplicates

# ── existing tests ────────────────────────────────────────────────────────────

def test_finds_duplicates():
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        c = Path(tmp) / "c.txt"
        a.write_text("hello duplicate")
        b.write_text("hello duplicate")
        c.write_text("unique content")

        groups = find_duplicates([Path(tmp)])
        assert len(groups) == 1
        paths = list(groups.values())[0]
        assert len(paths) == 2

def test_no_duplicates():
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "x.txt").write_text("aaa")
        Path(tmp, "y.txt").write_text("bbb")
        groups = find_duplicates([Path(tmp)])
        assert len(groups) == 0

# ── v1.1.0: --type ────────────────────────────────────────────────────────────

def test_type_filter_finds_matching():
    """Duplicate .jpg files are found when --type .jpg is set."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.jpg").write_bytes(b"image data")
        Path(tmp, "b.jpg").write_bytes(b"image data")
        Path(tmp, "c.txt").write_bytes(b"image data")  # same content, wrong type

        groups = find_duplicates([Path(tmp)], types={".jpg"})
        assert len(groups) == 1
        for p in list(groups.values())[0]:
            assert p.suffix == ".jpg"

def test_type_filter_excludes_other_extensions():
    """Duplicate .txt files are NOT found when --type .jpg is set."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.txt").write_bytes(b"hello")
        Path(tmp, "b.txt").write_bytes(b"hello")

        groups = find_duplicates([Path(tmp)], types={".jpg"})
        assert len(groups) == 0

def test_type_filter_case_insensitive():
    """Extension matching is case-insensitive (.JPG matches .jpg filter)."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.JPG").write_bytes(b"photo")
        Path(tmp, "b.jpg").write_bytes(b"photo")

        groups = find_duplicates([Path(tmp)], types={".jpg"})
        assert len(groups) == 1

def test_multiple_types():
    """Multiple extensions can be filtered at once."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.jpg").write_bytes(b"img")
        Path(tmp, "b.jpg").write_bytes(b"img")
        Path(tmp, "c.png").write_bytes(b"png")
        Path(tmp, "d.png").write_bytes(b"png")
        Path(tmp, "e.txt").write_bytes(b"txt")
        Path(tmp, "f.txt").write_bytes(b"txt")

        groups = find_duplicates([Path(tmp)], types={".jpg", ".png"})
        assert len(groups) == 2  # jpg group + png group

# ── v1.1.0: --exclude ─────────────────────────────────────────────────────────

def test_exclude_skips_folder():
    """Files inside an excluded folder are not scanned."""
    with tempfile.TemporaryDirectory() as tmp:
        skip = Path(tmp) / "node_modules"
        skip.mkdir()
        (skip / "a.txt").write_bytes(b"dup")
        (skip / "b.txt").write_bytes(b"dup")

        groups = find_duplicates([Path(tmp)], exclude={"node_modules"})
        assert len(groups) == 0

def test_exclude_does_not_affect_other_folders():
    """Duplicates outside excluded folders are still found."""
    with tempfile.TemporaryDirectory() as tmp:
        keep = Path(tmp) / "keep"
        keep.mkdir()
        (keep / "a.txt").write_bytes(b"dup")
        (keep / "b.txt").write_bytes(b"dup")

        skip = Path(tmp) / "node_modules"
        skip.mkdir()
        (skip / "c.txt").write_bytes(b"other dup")
        (skip / "d.txt").write_bytes(b"other dup")

        groups = find_duplicates([Path(tmp)], exclude={"node_modules"})
        assert len(groups) == 1  # only the 'keep' group

def test_exclude_case_insensitive():
    """Folder name matching is case-insensitive."""
    with tempfile.TemporaryDirectory() as tmp:
        skip = Path(tmp) / "Windows"
        skip.mkdir()
        (skip / "a.dll").write_bytes(b"sys")
        (skip / "b.dll").write_bytes(b"sys")

        groups = find_duplicates([Path(tmp)], exclude={"windows"})
        assert len(groups) == 0

def test_exclude_multiple_folders():
    """Multiple folders can be excluded at once."""
    with tempfile.TemporaryDirectory() as tmp:
        for folder in ("node_modules", ".git", "dist"):
            d = Path(tmp) / folder
            d.mkdir()
            (d / "a.txt").write_bytes(b"dup")
            (d / "b.txt").write_bytes(b"dup")

        groups = find_duplicates([Path(tmp)], exclude={"node_modules", ".git", "dist"})
        assert len(groups) == 0

# ── v1.1.0: --summary and --count (reporter) ─────────────────────────────────

def test_print_summary_output(capsys):
    """print_summary prints wasted space and group count."""
    import tempfile
    from dupegun.reporter import print_summary

    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        a.write_bytes(b"x" * 1024)
        b.write_bytes(b"x" * 1024)
        groups = find_duplicates([Path(tmp)])
        # Should not raise and should produce output
        print_summary(groups)

def test_print_count_output(capsys):
    """print_count prints group count line."""
    from dupegun.reporter import print_count

    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        a.write_bytes(b"y" * 512)
        b.write_bytes(b"y" * 512)
        groups = find_duplicates([Path(tmp)])
        print_count(groups)  # Should not raise

# ── combined ──────────────────────────────────────────────────────────────────

def test_type_and_exclude_combined():
    """--type and --exclude can be combined."""
    with tempfile.TemporaryDirectory() as tmp:
        good = Path(tmp) / "photos"
        good.mkdir()
        (good / "a.jpg").write_bytes(b"photo")
        (good / "b.jpg").write_bytes(b"photo")

        bad = Path(tmp) / "cache"
        bad.mkdir()
        (bad / "c.jpg").write_bytes(b"photo")  # excluded folder

        txt = Path(tmp) / "d.txt"   # wrong type
        txt2 = Path(tmp) / "e.txt"
        txt.write_bytes(b"photo")
        txt2.write_bytes(b"photo")

        groups = find_duplicates([Path(tmp)], types={".jpg"}, exclude={"cache"})
        assert len(groups) == 1
        for p in list(groups.values())[0]:
            assert p.suffix == ".jpg"
            assert "cache" not in str(p)
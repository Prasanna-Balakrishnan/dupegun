import os
import time
import tempfile
from pathlib import Path
from dupegun.scanner import find_duplicates, find_cross_duplicates

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
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.jpg").write_bytes(b"image data")
        Path(tmp, "b.jpg").write_bytes(b"image data")
        Path(tmp, "c.txt").write_bytes(b"image data")

        groups = find_duplicates([Path(tmp)], types={".jpg"})
        assert len(groups) == 1
        for p in list(groups.values())[0]:
            assert p.suffix == ".jpg"

def test_type_filter_excludes_other_extensions():
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.txt").write_bytes(b"hello")
        Path(tmp, "b.txt").write_bytes(b"hello")
        groups = find_duplicates([Path(tmp)], types={".jpg"})
        assert len(groups) == 0

def test_type_filter_case_insensitive():
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.JPG").write_bytes(b"photo")
        Path(tmp, "b.jpg").write_bytes(b"photo")
        groups = find_duplicates([Path(tmp)], types={".jpg"})
        assert len(groups) == 1

def test_multiple_types():
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.jpg").write_bytes(b"img")
        Path(tmp, "b.jpg").write_bytes(b"img")
        Path(tmp, "c.png").write_bytes(b"png")
        Path(tmp, "d.png").write_bytes(b"png")
        Path(tmp, "e.txt").write_bytes(b"txt")
        Path(tmp, "f.txt").write_bytes(b"txt")
        groups = find_duplicates([Path(tmp)], types={".jpg", ".png"})
        assert len(groups) == 2

# ── v1.1.0: --exclude ─────────────────────────────────────────────────────────

def test_exclude_skips_folder():
    with tempfile.TemporaryDirectory() as tmp:
        skip = Path(tmp) / "node_modules"
        skip.mkdir()
        (skip / "a.txt").write_bytes(b"dup")
        (skip / "b.txt").write_bytes(b"dup")
        groups = find_duplicates([Path(tmp)], exclude={"node_modules"})
        assert len(groups) == 0

def test_exclude_does_not_affect_other_folders():
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
        assert len(groups) == 1

def test_exclude_case_insensitive():
    with tempfile.TemporaryDirectory() as tmp:
        skip = Path(tmp) / "Windows"
        skip.mkdir()
        (skip / "a.dll").write_bytes(b"sys")
        (skip / "b.dll").write_bytes(b"sys")
        groups = find_duplicates([Path(tmp)], exclude={"windows"})
        assert len(groups) == 0

def test_exclude_multiple_folders():
    with tempfile.TemporaryDirectory() as tmp:
        for folder in ("node_modules", ".git", "dist"):
            d = Path(tmp) / folder
            d.mkdir()
            (d / "a.txt").write_bytes(b"dup")
            (d / "b.txt").write_bytes(b"dup")
        groups = find_duplicates([Path(tmp)], exclude={"node_modules", ".git", "dist"})
        assert len(groups) == 0

# ── v1.1.0: --summary and --count ────────────────────────────────────────────

def test_print_summary_output(capsys):
    from dupegun.reporter import print_summary
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        a.write_bytes(b"x" * 1024)
        b.write_bytes(b"x" * 1024)
        groups = find_duplicates([Path(tmp)])
        print_summary(groups)

def test_print_count_output(capsys):
    from dupegun.reporter import print_count
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        a.write_bytes(b"y" * 512)
        b.write_bytes(b"y" * 512)
        groups = find_duplicates([Path(tmp)])
        print_count(groups)

# ── v1.1.0: combined ─────────────────────────────────────────────────────────

def test_type_and_exclude_combined():
    with tempfile.TemporaryDirectory() as tmp:
        good = Path(tmp) / "photos"
        good.mkdir()
        (good / "a.jpg").write_bytes(b"photo")
        (good / "b.jpg").write_bytes(b"photo")
        bad = Path(tmp) / "cache"
        bad.mkdir()
        (bad / "c.jpg").write_bytes(b"photo")
        txt = Path(tmp) / "d.txt"
        txt2 = Path(tmp) / "e.txt"
        txt.write_bytes(b"photo")
        txt2.write_bytes(b"photo")
        groups = find_duplicates([Path(tmp)], types={".jpg"}, exclude={"cache"})
        assert len(groups) == 1
        for p in list(groups.values())[0]:
            assert p.suffix == ".jpg"
            assert "cache" not in str(p)

# ── v1.2.0: --max-size ───────────────────────────────────────────────────────

def test_max_size_excludes_large_files():
    """Files larger than max_size are not scanned."""
    with tempfile.TemporaryDirectory() as tmp:
        # Two identical big files (2000 bytes) — should be excluded
        Path(tmp, "big_a.txt").write_bytes(b"x" * 2000)
        Path(tmp, "big_b.txt").write_bytes(b"x" * 2000)
        # Two identical small files (100 bytes) — should be found
        Path(tmp, "small_a.txt").write_bytes(b"y" * 100)
        Path(tmp, "small_b.txt").write_bytes(b"y" * 100)

        groups = find_duplicates([Path(tmp)], max_size=500)
        assert len(groups) == 1
        for p in list(groups.values())[0]:
            assert p.stat().st_size <= 500

def test_max_size_no_limit():
    """max_size=None imposes no upper limit."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.txt").write_bytes(b"z" * 5000)
        Path(tmp, "b.txt").write_bytes(b"z" * 5000)
        groups = find_duplicates([Path(tmp)], max_size=None)
        assert len(groups) == 1

def test_min_size_and_max_size_range():
    """min_size and max_size together form a range."""
    with tempfile.TemporaryDirectory() as tmp:
        # Too small (< 100 bytes)
        Path(tmp, "tiny_a.bin").write_bytes(b"t" * 50)
        Path(tmp, "tiny_b.bin").write_bytes(b"t" * 50)
        # In range [100, 1000]
        Path(tmp, "mid_a.bin").write_bytes(b"m" * 500)
        Path(tmp, "mid_b.bin").write_bytes(b"m" * 500)
        # Too large (> 1000 bytes)
        Path(tmp, "big_a.bin").write_bytes(b"b" * 2000)
        Path(tmp, "big_b.bin").write_bytes(b"b" * 2000)

        groups = find_duplicates([Path(tmp)], min_size=100, max_size=1000)
        assert len(groups) == 1
        for p in list(groups.values())[0]:
            size = p.stat().st_size
            assert 100 <= size <= 1000

# ── v1.2.0: --pattern ────────────────────────────────────────────────────────

def test_pattern_matches_filenames():
    """Only files whose names match the regex are scanned."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "Copy of report.pdf").write_bytes(b"doc")
        Path(tmp, "Copy of photo.jpg").write_bytes(b"doc")  # same content
        Path(tmp, "original.pdf").write_bytes(b"doc")       # same content, no match

        # Only 'Copy of*' files → two matches with same content
        groups = find_duplicates([Path(tmp)], pattern=r"Copy of.*")
        assert len(groups) == 1
        for p in list(groups.values())[0]:
            assert p.name.startswith("Copy of")

def test_pattern_no_matches():
    """A pattern that matches nothing finds no duplicates."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.txt").write_bytes(b"hello")
        Path(tmp, "b.txt").write_bytes(b"hello")

        groups = find_duplicates([Path(tmp)], pattern=r"^IMG_\d+")
        assert len(groups) == 0

def test_pattern_case_insensitive():
    """Pattern matching is case-insensitive."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "COPY OF report.pdf").write_bytes(b"data")
        Path(tmp, "copy of report2.pdf").write_bytes(b"data")

        groups = find_duplicates([Path(tmp)], pattern=r"copy of.*")
        assert len(groups) == 1

def test_pattern_and_type_combined():
    """--pattern and --type can be combined."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "Copy of img.jpg").write_bytes(b"img")
        Path(tmp, "Copy of img2.jpg").write_bytes(b"img")  # dup jpg, matches
        Path(tmp, "Copy of doc.txt").write_bytes(b"img")   # dup content, wrong type

        groups = find_duplicates([Path(tmp)], pattern=r"Copy of.*", types={".jpg"})
        assert len(groups) == 1
        for p in list(groups.values())[0]:
            assert p.suffix == ".jpg"

# ── v1.2.0: compare (cross-directory duplicates) ─────────────────────────────

def test_compare_finds_cross_duplicates():
    """find_cross_duplicates detects files with same content in both directories."""
    with tempfile.TemporaryDirectory() as dir_a, \
         tempfile.TemporaryDirectory() as dir_b:

        Path(dir_a, "file1.txt").write_bytes(b"shared content")
        Path(dir_b, "file1_backup.txt").write_bytes(b"shared content")
        Path(dir_a, "unique_a.txt").write_bytes(b"only in A")
        Path(dir_b, "unique_b.txt").write_bytes(b"only in B")

        cross = find_cross_duplicates(Path(dir_a), Path(dir_b))
        assert len(cross) == 1
        entry = list(cross.values())[0]
        assert len(entry["a"]) == 1
        assert len(entry["b"]) == 1

def test_compare_no_cross_duplicates():
    """No cross duplicates when directories have entirely different content."""
    with tempfile.TemporaryDirectory() as dir_a, \
         tempfile.TemporaryDirectory() as dir_b:

        Path(dir_a, "a.txt").write_bytes(b"content A")
        Path(dir_b, "b.txt").write_bytes(b"content B")

        cross = find_cross_duplicates(Path(dir_a), Path(dir_b))
        assert len(cross) == 0

def test_compare_respects_type_filter():
    """--type filter is applied when comparing."""
    with tempfile.TemporaryDirectory() as dir_a, \
         tempfile.TemporaryDirectory() as dir_b:

        Path(dir_a, "photo.jpg").write_bytes(b"pixels")
        Path(dir_b, "photo_bak.jpg").write_bytes(b"pixels")   # cross-dup jpg
        Path(dir_a, "doc.txt").write_bytes(b"pixels")          # same bytes, wrong type
        Path(dir_b, "doc_bak.txt").write_bytes(b"pixels")

        cross = find_cross_duplicates(
            Path(dir_a), Path(dir_b), types={".jpg"}
        )
        assert len(cross) == 1
        for p in list(cross.values())[0]["a"] + list(cross.values())[0]["b"]:
            assert p.suffix == ".jpg"

def test_compare_respects_max_size():
    """max_size filter is respected in compare."""
    with tempfile.TemporaryDirectory() as dir_a, \
         tempfile.TemporaryDirectory() as dir_b:

        Path(dir_a, "big.bin").write_bytes(b"x" * 5000)
        Path(dir_b, "big2.bin").write_bytes(b"x" * 5000)

        cross = find_cross_duplicates(Path(dir_a), Path(dir_b), max_size=100)
        assert len(cross) == 0

# ── v1.2.0: --older-than ─────────────────────────────────────────────────────

def test_older_than_skips_recent_files():
    """Files modified within the threshold are NOT deleted."""
    from dupegun.actions import delete_dupes

    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        a.write_bytes(b"dup content")
        b.write_bytes(b"dup content")

        # Both files are brand-new → older_than=30 should skip both
        groups = find_duplicates([Path(tmp)])
        assert len(groups) == 1

        deleted = []
        original_unlink = Path.unlink

        # Monkey-patch to track deletes — should NOT be called
        def track_unlink(self):
            deleted.append(self)
            original_unlink(self)

        import unittest.mock as mock
        with mock.patch.object(Path, "unlink", track_unlink):
            delete_dupes(groups, strategy="shortest", dry_run=False, older_than=30)

        # Nothing should have been deleted since both files are fresh
        assert len(deleted) == 0

def test_older_than_deletes_old_files():
    """Files older than the threshold ARE deleted."""
    from dupegun.actions import delete_dupes

    with tempfile.TemporaryDirectory() as tmp:
        keeper = Path(tmp) / "keeper.txt"
        old    = Path(tmp) / "old_copy.txt"
        keeper.write_bytes(b"dup content")
        old.write_bytes(b"dup content")

        # Force old_copy to be 60 days old
        old_ts = time.time() - 60 * 86_400
        os.utime(old, (old_ts, old_ts))

        groups = find_duplicates([Path(tmp)])
        assert len(groups) == 1

        delete_dupes(groups, strategy="newest", dry_run=False, older_than=30)

        assert not old.exists(), "old file should have been deleted"
        assert keeper.exists(), "keeper should still exist"
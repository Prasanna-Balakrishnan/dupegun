import os
import tempfile
from pathlib import Path
from dupegun.scanner import find_duplicates

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
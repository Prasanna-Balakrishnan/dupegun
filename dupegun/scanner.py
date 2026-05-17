import os
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Iterator, Optional, Set

CHUNK = 65_536

def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()

def _partial_hash(path: Path, size: int = 4096) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(size))
    return h.hexdigest()

def walk_files(
    root: Path,
    min_size: int = 1,
    types: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
) -> Iterator[Path]:
    """
    Recursively yield files under *root*.

    Args:
        root:    Directory to walk.
        min_size: Skip files smaller than this many bytes.
        types:   If given, only yield files whose suffix (e.g. '.jpg') is in
                 this set. Comparison is case-insensitive.
        exclude: Folder *names* (not full paths) to skip entirely, e.g.
                 {'node_modules', '.git', 'Windows'}.
    """
    # Normalise once so comparisons are always lowercase
    norm_types = {t.lower() for t in types} if types else None
    norm_exclude = {e.lower() for e in exclude} if exclude else None

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories in-place so os.walk won't descend into them
        if norm_exclude:
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in norm_exclude
            ]

        for name in filenames:
            p = Path(dirpath) / name

            # Extension filter
            if norm_types and p.suffix.lower() not in norm_types:
                continue

            try:
                if p.stat().st_size >= min_size:
                    yield p
            except (PermissionError, OSError):
                pass

def find_duplicates(
    roots: list,
    min_size: int = 1,
    progress_cb=None,
    types: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
) -> dict:
    by_size = defaultdict(list)
    all_files = [
        f
        for root in roots
        for f in walk_files(root, min_size, types=types, exclude=exclude)
    ]

    for path in all_files:
        by_size[path.stat().st_size].append(path)

    size_candidates = [
        p for files in by_size.values()
        if len(files) > 1
        for p in files
    ]

    by_partial = defaultdict(list)
    for path in size_candidates:
        try:
            by_partial[_partial_hash(path)].append(path)
        except (PermissionError, OSError):
            pass

    partial_candidates = [
        p for files in by_partial.values()
        if len(files) > 1
        for p in files
    ]

    by_hash = defaultdict(list)
    total = len(partial_candidates)
    for i, path in enumerate(partial_candidates):
        if progress_cb:
            progress_cb(i + 1, total, path)
        try:
            by_hash[_hash_file(path)].append(path)
        except (PermissionError, OSError):
            pass

    return {h: paths for h, paths in by_hash.items() if len(paths) > 1}
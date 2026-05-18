import os
import re
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
    max_size: Optional[int] = None,
    types: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
    pattern: Optional[str] = None,
) -> Iterator[Path]:
    """
    Recursively yield files under *root*.

    Args:
        root:     Directory to walk.
        min_size: Skip files smaller than this many bytes.
        max_size: Skip files larger than this many bytes (None = no limit).
        types:    If given, only yield files whose suffix (e.g. '.jpg') is in
                  this set. Comparison is case-insensitive.
        exclude:  Folder *names* (not full paths) to skip entirely, e.g.
                  {'node_modules', '.git', 'Windows'}.
        pattern:  Regex pattern matched against the filename (not full path).
                  e.g. r'Copy of.*' or r'.*\\.jpg'. Case-insensitive.
    """
    norm_types   = {t.lower() for t in types}   if types   else None
    norm_exclude = {e.lower() for e in exclude}  if exclude else None
    compiled_pat = re.compile(pattern, re.IGNORECASE) if pattern else None

    for dirpath, dirnames, filenames in os.walk(root):
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

            # Regex filename filter
            if compiled_pat and not compiled_pat.search(name):
                continue

            try:
                size = p.stat().st_size
                if size < min_size:
                    continue
                if max_size is not None and size > max_size:
                    continue
                yield p
            except (PermissionError, OSError):
                pass


def find_duplicates(
    roots: list,
    min_size: int = 1,
    max_size: Optional[int] = None,
    progress_cb=None,
    types: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
    pattern: Optional[str] = None,
) -> dict:
    """Find duplicate files across all *roots* and return a hash → [Path] dict."""
    by_size = defaultdict(list)
    all_files = [
        f
        for root in roots
        for f in walk_files(
            root,
            min_size=min_size,
            max_size=max_size,
            types=types,
            exclude=exclude,
            pattern=pattern,
        )
    ]

    for path in all_files:
        try:
            by_size[path.stat().st_size].append(path)
        except (PermissionError, OSError):
            pass

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


def find_cross_duplicates(
    root_a: Path,
    root_b: Path,
    min_size: int = 1,
    max_size: Optional[int] = None,
    types: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
    pattern: Optional[str] = None,
    progress_cb=None,
) -> dict:
    """
    Find files that exist in BOTH *root_a* and *root_b* (cross-directory duplicates).

    Returns a dict: hash → {'a': [Path, ...], 'b': [Path, ...]}
    Only hashes that appear in both sides are included.
    """
    walk_kwargs = dict(
        min_size=min_size,
        max_size=max_size,
        types=types,
        exclude=exclude,
        pattern=pattern,
    )

    files_a = list(walk_files(root_a, **walk_kwargs))
    files_b = list(walk_files(root_b, **walk_kwargs))

    # Build hash → [Path] for side A
    hashes_a: dict = defaultdict(list)
    total = len(files_a) + len(files_b)
    done = 0
    for path in files_a:
        if progress_cb:
            progress_cb(done + 1, total, path)
        done += 1
        try:
            hashes_a[_hash_file(path)].append(path)
        except (PermissionError, OSError):
            pass

    # Build hash → [Path] for side B — only hash if it might match A
    hashes_b: dict = defaultdict(list)
    for path in files_b:
        if progress_cb:
            progress_cb(done + 1, total, path)
        done += 1
        try:
            h = _hash_file(path)
            if h in hashes_a:          # only keep if already seen in A
                hashes_b[h].append(path)
        except (PermissionError, OSError):
            pass

    # Keep only hashes present in both sides
    result = {}
    for h, paths_a in hashes_a.items():
        if h in hashes_b:
            result[h] = {"a": paths_a, "b": hashes_b[h]}
    return result
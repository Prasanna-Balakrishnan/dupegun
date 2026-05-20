"""
dupegun watch mode
===================

Monitors a folder for new files and alerts when a duplicate appears.

Usage
-----
    dupegun watch ~/Downloads
    dupegun watch ~/Downloads --min-size 1MB --type .jpg

Requires the `watchdog` library:
    pip install watchdog
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Set

from rich.console import Console
from rich.panel import Panel

from .scanner import _hash_file
from .reporter import human_size

console = Console()

# ── watchdog import guard ─────────────────────────────────────────────────────

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False


def _check_watchdog() -> None:
    if not _WATCHDOG_AVAILABLE:
        raise SystemExit(
            "\n[dupegun] Watch mode requires the 'watchdog' library.\n"
            "Install it with:  pip install watchdog\n"
        )


# ── event handler ─────────────────────────────────────────────────────────────

if _WATCHDOG_AVAILABLE:

    class DupeWatchHandler(FileSystemEventHandler):
        """
        Watches a directory tree and checks every new/modified file against
        a hash index of all already-seen files.
        """

        def __init__(
            self,
            root: Path,
            min_size: int = 1,
            max_size: Optional[int] = None,
            types: Optional[Set[str]] = None,
            exclude: Optional[Set[str]] = None,
        ):
            super().__init__()
            self.root     = root
            self.min_size = min_size
            self.max_size = max_size
            self.norm_types   = {t.lower() for t in types}   if types   else None
            self.norm_exclude = {e.lower() for e in exclude}  if exclude else None

            # Bootstrap hash index from existing files
            self._hash_index: dict[str, Path] = {}
            self._build_index()

        def _build_index(self) -> None:
            """Hash all existing files into the index."""
            count = 0
            for dirpath, dirnames, filenames in __import__("os").walk(self.root):
                if self.norm_exclude:
                    dirnames[:] = [
                        d for d in dirnames
                        if d.lower() not in self.norm_exclude
                    ]
                for name in filenames:
                    p = Path(dirpath) / name
                    if self._passes_filters(p):
                        try:
                            h = _hash_file(p)
                            self._hash_index.setdefault(h, p)
                            count += 1
                        except (PermissionError, OSError):
                            pass
            console.print(
                f"[dim]Indexed {count:,} existing file(s). "
                f"Watching for duplicates...[/dim]"
            )

        def _passes_filters(self, p: Path) -> bool:
            if self.norm_types and p.suffix.lower() not in self.norm_types:
                return False
            try:
                size = p.stat().st_size
                if size < self.min_size:
                    return False
                if self.max_size is not None and size > self.max_size:
                    return False
            except (OSError, PermissionError):
                return False
            return True

        def _check_file(self, path_str: str) -> None:
            p = Path(path_str)
            if not p.is_file():
                return
            if not self._passes_filters(p):
                return

            try:
                h = _hash_file(p)
            except (PermissionError, OSError):
                return

            if h in self._hash_index:
                original = self._hash_index[h]
                try:
                    size = p.stat().st_size
                except (OSError, PermissionError):
                    size = 0

                console.print(Panel(
                    f"[bold red]DUPLICATE DETECTED[/bold red]\n\n"
                    f"  [bold]New file:[/bold]      [cyan]{p}[/cyan]\n"
                    f"  [bold]Matches:[/bold]       [yellow]{original}[/yellow]\n"
                    f"  [bold]Size:[/bold]          {human_size(size)}\n"
                    f"  [bold]SHA-256:[/bold]       [dim]{h[:32]}...[/dim]",
                    title="dupegun watch",
                    border_style="red",
                ))
            else:
                # New unique file — add to index
                self._hash_index[h] = p
                console.print(f"[dim]  + {p.name}[/dim]")

        def on_created(self, event: FileCreatedEvent) -> None:
            if not event.is_directory:
                # Small delay to let the file finish writing
                time.sleep(0.5)
                self._check_file(event.src_path)

        def on_modified(self, event: FileModifiedEvent) -> None:
            if not event.is_directory:
                time.sleep(0.5)
                self._check_file(event.src_path)


# ── public entry point ────────────────────────────────────────────────────────

def run_watch(
    root: Path,
    min_size: int = 1,
    max_size: Optional[int] = None,
    types: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
) -> None:
    """
    Start watching *root* for duplicate files.

    Press Ctrl+C to stop.

    Args:
        root:     Directory to monitor.
        min_size: Ignore files smaller than this many bytes.
        max_size: Ignore files larger than this many bytes.
        types:    If given, only watch files with these extensions.
        exclude:  Folder names to ignore.
    """
    _check_watchdog()

    handler  = DupeWatchHandler(
        root, min_size=min_size, max_size=max_size,
        types=types, exclude=exclude,
    )
    observer = Observer()
    observer.schedule(handler, str(root), recursive=True)
    observer.start()

    console.print(
        f"\n[bold green]dupegun watch[/bold green] — "
        f"monitoring [cyan]{root}[/cyan]\n"
        f"[dim]Press Ctrl+C to stop.[/dim]\n"
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[dim]Watch stopped.[/dim]")

    observer.join()
"""
dupegun restore
================

Undo deletions recorded in a --log file produced by `dupegun delete --log`.

Each line in the log is a TSV row:
    timestamp  action  kept=<path>  deleted=<path>  size=<bytes>

`restore` reads the log, finds entries where action == "deleted", and
moves the *kept* file back to the *deleted* path — effectively reversing
the deletion by copying the keeper to where the duplicate used to live.

Note: the original deleted file is gone; restore creates a fresh copy
from the keeper so both paths exist again with identical content.

Usage
-----
    dupegun restore deleted.log
    dupegun restore deleted.log --dry-run
"""

from __future__ import annotations

import shutil
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


def _parse_log(log_path: str) -> list[dict]:
    """
    Parse a dupegun deletion log file.

    Returns a list of dicts with keys:
        timestamp, action, kept, deleted, size_bytes
    """
    entries = []
    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                console.print(
                    f"[yellow]Line {line_no}: skipping malformed entry[/yellow]"
                )
                continue
            try:
                entry = {
                    "timestamp":  parts[0],
                    "action":     parts[1],
                    "kept":       parts[2].removeprefix("kept="),
                    "deleted":    parts[3].removeprefix("deleted="),
                    "size_bytes": int(parts[4].removeprefix("size=")),
                }
                entries.append(entry)
            except (ValueError, IndexError):
                console.print(
                    f"[yellow]Line {line_no}: skipping malformed entry[/yellow]"
                )

    return entries


def restore_from_log(log_path: str, dry_run: bool = True) -> None:
    """
    Restore deleted files using a dupegun deletion log.

    For each logged deletion, copies the *kept* file back to the path
    where the *deleted* file used to live.

    Args:
        log_path: Path to the TSV log file produced by --log.
        dry_run:  If True, only preview — nothing is copied.
    """
    entries = _parse_log(log_path)
    deletions = [e for e in entries if e["action"] == "deleted"]

    if not deletions:
        console.print("[bold green]No deletions found in log.[/bold green]")
        return

    console.print(
        f"\n[bold]dupegun restore[/bold] — "
        f"{len(deletions)} deletion(s) found in log\n"
    )

    if dry_run:
        console.print(
            "[yellow]DRY RUN — nothing will be restored. "
            "Use --no-dry-run to actually restore.[/yellow]\n"
        )

    # Summary table
    t = Table(show_lines=True)
    t.add_column("Timestamp",   style="dim",    width=18)
    t.add_column("Restore to",  style="red")
    t.add_column("Copy from",   style="green")
    t.add_column("Size",        justify="right")

    from .reporter import human_size
    for e in deletions:
        t.add_row(
            e["timestamp"],
            e["deleted"],
            e["kept"],
            human_size(e["size_bytes"]),
        )
    console.print(t)
    console.print()

    if dry_run:
        return

    restored = 0
    skipped  = 0
    errors   = 0

    for e in deletions:
        src  = Path(e["kept"])
        dest = Path(e["deleted"])

        if not src.exists():
            console.print(
                f"[yellow]Skipping — keeper no longer exists: {src}[/yellow]"
            )
            skipped += 1
            continue

        if dest.exists():
            console.print(
                f"[yellow]Skipping — destination already exists: {dest}[/yellow]"
            )
            skipped += 1
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dest))
            console.print(f"[green]Restored[/green] {dest}")
            restored += 1
        except OSError as err:
            console.print(f"[red]Error restoring {dest}: {err}[/red]")
            errors += 1

    console.print(
        f"\n[bold green]Restored {restored}[/bold green] file(s)  "
        f"[dim]|[/dim]  "
        f"[yellow]Skipped {skipped}[/yellow]  "
        f"[dim]|[/dim]  "
        + (f"[red]Errors {errors}[/red]" if errors else "[dim]Errors 0[/dim]")
        + "\n"
    )

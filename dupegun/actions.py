import os
import time
import shutil
import datetime
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from .reporter import human_size

console = Console()


def pick_keeper(paths: list, strategy: str) -> Path:
    if strategy == "newest":
        return max(paths, key=lambda p: p.stat().st_mtime)
    if strategy == "oldest":
        return min(paths, key=lambda p: p.stat().st_mtime)
    # default: shortest path
    return min(paths, key=lambda p: len(str(p)))


def _write_log(log_path: str, entries: list) -> None:
    """
    Append deletion log entries to *log_path*.

    Each entry is a dict with keys: timestamp, action, kept, deleted, size_bytes.
    """
    with open(log_path, "a", encoding="utf-8", newline="") as f:
        for e in entries:
            f.write(
                f"{e['timestamp']}\t"
                f"{e['action']}\t"
                f"kept={e['kept']}\t"
                f"deleted={e['deleted']}\t"
                f"size={e['size_bytes']}\n"
            )


def delete_dupes(
    groups: dict,
    strategy: str = "shortest",
    dry_run: bool = True,
    interactive: bool = False,
    older_than: int = None,
    log_path: str = None,
) -> None:
    """
    Delete duplicate files, keeping one copy per group.

    Args:
        groups:      Hash -> [Path, ...] from find_duplicates.
        strategy:    Which copy to keep ('shortest', 'newest', 'oldest').
        dry_run:     If True, only preview — nothing is deleted.
        interactive: Prompt before each group.
        older_than:  Only delete copies older than this many days.
        log_path:    If set, append a TSV log of every deletion to this file.
    """
    total_freed = 0
    cutoff_ts   = (time.time() - older_than * 86_400) if older_than else None
    log_entries = []

    for hash_val, paths in groups.items():
        keeper    = pick_keeper(paths, strategy)
        to_delete = [p for p in paths if p != keeper]

        if cutoff_ts is not None:
            to_delete = [
                p for p in to_delete
                if p.stat().st_mtime < cutoff_ts
            ]

        if not to_delete:
            continue

        console.print(f"\n[bold]Keep:[/bold]   [green]{keeper}[/green]")
        for p in to_delete:
            try:
                age_days = (time.time() - p.stat().st_mtime) / 86_400
                age_str  = f"  [dim]({age_days:.0f} days old)[/dim]"
            except (OSError, PermissionError):
                age_str = ""
            console.print(f"[bold]Delete:[/bold] [red]{p}[/red]{age_str}")

        if interactive:
            if not Confirm.ask("  Proceed with this group?"):
                continue

        for p in to_delete:
            try:
                size = p.stat().st_size
            except (OSError, PermissionError):
                size = 0

            if dry_run:
                console.print(f"  [dim][DRY RUN] would delete {p}[/dim]")
            else:
                try:
                    p.unlink()
                    total_freed += size
                    console.print(f"  [red]Deleted {p}[/red]")
                    log_entries.append({
                        "timestamp":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "action":     "deleted",
                        "kept":       str(keeper),
                        "deleted":    str(p),
                        "size_bytes": size,
                    })
                except OSError as e:
                    console.print(f"  [yellow]Error: {e}[/yellow]")

    if not dry_run:
        console.print(
            f"\n[bold green]Freed {human_size(total_freed)}[/bold green]"
        )
        if log_path and log_entries:
            _write_log(log_path, log_entries)
            console.print(f"[green]Log saved → {log_path}[/green]")


def move_dupes(
    groups: dict,
    dest: Path,
    strategy: str = "shortest",
    dry_run: bool = True,
) -> None:
    dest.mkdir(parents=True, exist_ok=True)

    for hash_val, paths in groups.items():
        keeper = pick_keeper(paths, strategy)
        for p in paths:
            if p == keeper:
                continue
            target = dest / p.name
            if target.exists():
                target = dest / f"{hash_val[:8]}_{p.name}"

            if dry_run:
                console.print(
                    f"[dim][DRY RUN] would move {p} → {target}[/dim]"
                )
            else:
                shutil.move(str(p), str(target))
                console.print(f"[yellow]Moved {p} → {target}[/yellow]")


def hardlink_dupes(
    groups: dict,
    strategy: str = "shortest",
    dry_run: bool = True,
) -> None:
    for hash_val, paths in groups.items():
        keeper = pick_keeper(paths, strategy)
        for p in paths:
            if p == keeper:
                continue
            if dry_run:
                console.print(
                    f"[dim][DRY RUN] would hardlink {p} → {keeper}[/dim]"
                )
            else:
                try:
                    p.unlink()
                    os.link(keeper, p)
                    console.print(
                        f"[cyan]Hardlinked {p} → {keeper}[/cyan]"
                    )
                except OSError as e:
                    console.print(f"[yellow]Error: {e}[/yellow]")
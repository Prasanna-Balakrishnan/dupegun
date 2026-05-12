import os
import shutil
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
    if strategy == "shortest":
        return min(paths, key=lambda p: len(str(p)))
    return paths[0]

def delete_dupes(
    groups: dict,
    strategy: str = "shortest",
    dry_run: bool = True,
    interactive: bool = False,
) -> None:
    total_freed = 0

    for hash_val, paths in groups.items():
        keeper = pick_keeper(paths, strategy)
        to_delete = [p for p in paths if p != keeper]

        console.print(f"\n[bold]Keep:[/bold]   [green]{keeper}[/green]")
        for p in to_delete:
            console.print(f"[bold]Delete:[/bold] [red]{p}[/red]")

        if interactive:
            if not Confirm.ask("  Proceed with this group?"):
                continue

        for p in to_delete:
            size = p.stat().st_size
            if dry_run:
                console.print(f"  [dim][DRY RUN] would delete {p}[/dim]")
            else:
                try:
                    p.unlink()
                    total_freed += size
                    console.print(f"  [red]Deleted {p}[/red]")
                except OSError as e:
                    console.print(f"  [yellow]Error: {e}[/yellow]")

    if not dry_run:
        console.print(
            f"\n[bold green]Freed {human_size(total_freed)}[/bold green]"
        )

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
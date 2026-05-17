import json
import csv
import datetime
from pathlib import Path
from rich.table import Table
from rich.console import Console

console = Console()

def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

def _wasted(groups: dict) -> int:
    """Total bytes wasted across all duplicate groups."""
    total = 0
    for paths in groups.values():
        try:
            size = paths[0].stat().st_size
        except (OSError, PermissionError):
            size = 0
        total += size * (len(paths) - 1)
    return total

def print_table(groups: dict) -> None:
    total_wasted = 0

    for i, (hash_val, paths) in enumerate(groups.items(), 1):
        size = paths[0].stat().st_size
        wasted = size * (len(paths) - 1)
        total_wasted += wasted

        t = Table(
            title=f"[bold]Group {i}[/bold] — {human_size(size)} each  |  "
                  f"[red]{human_size(wasted)} wasted[/red]",
            show_lines=True,
        )
        t.add_column("#", style="dim", width=4)
        t.add_column("Path", style="cyan")
        t.add_column("Modified", style="yellow")
        t.add_column("Size", justify="right")

        for j, p in enumerate(paths, 1):
            stat = p.stat()
            mtime = datetime.datetime.fromtimestamp(
                stat.st_mtime
            ).strftime("%Y-%m-%d %H:%M")
            t.add_row(str(j), str(p), mtime, human_size(stat.st_size))

        console.print(t)

    console.print(
        f"\n[bold green]Total reclaimable:[/bold green] "
        f"[green]{human_size(total_wasted)}[/green] "
        f"across [bold]{len(groups)}[/bold] duplicate group(s)\n"
    )

def print_summary(groups: dict) -> None:
    """Print a single-line summary — total wasted space, no file list."""
    total_wasted = _wasted(groups)
    console.print(
        f"\n[bold green]Total reclaimable:[/bold green] "
        f"[green]{human_size(total_wasted)}[/green] "
        f"across [bold]{len(groups)}[/bold] duplicate group(s)\n"
    )

def print_count(groups: dict) -> None:
    """Print duplicate group count and wasted space, then exit."""
    total_wasted = _wasted(groups)
    console.print(
        f"\n[bold]{len(groups)}[/bold] duplicate group(s) found, "
        f"[red]{human_size(total_wasted)}[/red] wasted\n"
    )

def export_json(groups: dict, out_path: str) -> None:
    data = [
        {
            "hash": h,
            "count": len(paths),
            "size_each": paths[0].stat().st_size,
            "files": [str(p) for p in paths]
        }
        for h, paths in groups.items()
    ]
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    console.print(f"[green]Exported JSON → {out_path}[/green]")

def export_csv(groups: dict, out_path: str) -> None:
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "hash", "path", "size_bytes", "modified"])
        for i, (h, paths) in enumerate(groups.items(), 1):
            for p in paths:
                stat = p.stat()
                mtime = datetime.datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%Y-%m-%d %H:%M")
                w.writerow([i, h, str(p), stat.st_size, mtime])
    console.print(f"[green]Exported CSV → {out_path}[/green]")
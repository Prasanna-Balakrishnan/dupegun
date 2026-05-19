import click
from pathlib import Path
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn,
    TextColumn, BarColumn, TaskProgressColumn,
)

from .scanner import find_duplicates, find_cross_duplicates, walk_files
from .reporter import (
    print_table, print_summary, print_count, print_stats,
    print_comparison, export_json, export_csv, export_html,
)
from .actions import delete_dupes, move_dupes, hardlink_dupes

console = Console()

# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_size(value: str) -> int:
    if value is None:
        return None
    s = value.strip().upper()
    units = [
        ("TB", 1024 ** 4),
        ("GB", 1024 ** 3),
        ("MB", 1024 ** 2),
        ("KB", 1024),
        ("B",  1),
    ]
    for suffix, mult in units:
        if s.endswith(suffix):
            try:
                return int(float(s[: -len(suffix)]) * mult)
            except ValueError:
                raise click.BadParameter(
                    f"Cannot parse size '{value}'. "
                    "Use formats like: 1, 500B, 1KB, 1.5MB, 2GB"
                )
    try:
        return int(s)
    except ValueError:
        raise click.BadParameter(
            f"Cannot parse size '{value}'. "
            "Use formats like: 1, 500B, 1KB, 1.5MB, 2GB"
        )


def _normalise_types(types: tuple):
    if not types:
        return None
    return {t if t.startswith(".") else f".{t}" for t in types}


def _scan(paths, min_size_str, max_size_str=None, types=None,
          exclude=None, pattern=None):
    roots    = [Path(p) for p in paths]
    min_size = _parse_size(min_size_str) if isinstance(min_size_str, str) else min_size_str
    max_size = _parse_size(max_size_str) if max_size_str else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning...", total=None)

        def cb(done, total, path):
            progress.update(
                task, completed=done, total=total,
                description=f"Hashing [cyan]{path.name}[/cyan]",
            )

        groups = find_duplicates(
            roots,
            min_size=min_size,
            max_size=max_size,
            progress_cb=cb,
            types=types,
            exclude=exclude,
            pattern=pattern,
        )
    return groups


def _common_scan_opts(fn):
    """Options shared by scan, delete, move, hardlink."""
    fn = click.option(
        "--min-size", default="1",
        help="Minimum file size (e.g. 1, 500B, 1KB, 1MB). Default: 1",
    )(fn)
    fn = click.option(
        "--max-size", default=None,
        help="Maximum file size (e.g. 100MB, 2GB). Default: no limit",
    )(fn)
    fn = click.option(
        "--type", "types", multiple=True, metavar="EXT",
        help="Only scan files with this extension (repeatable)",
    )(fn)
    fn = click.option(
        "--exclude", multiple=True, metavar="NAME",
        help="Skip folders with this name (repeatable)",
    )(fn)
    fn = click.option(
        "--pattern", default=None, metavar="REGEX",
        help='Only scan filenames matching this regex (e.g. --pattern "Copy of.*")',
    )(fn)
    return fn

# ── CLI group ─────────────────────────────────────────────────────────────────

@click.group()
@click.version_option("1.3.0", prog_name="dupegun")
def main():
    """dupegun — find and destroy duplicate files.

    Works on Windows, Linux and macOS. All file types supported.
    """
    pass

# ── scan ──────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@_common_scan_opts
@click.option("--summary", is_flag=True,
              help="Print total wasted space only, no file list")
@click.option("--count",   is_flag=True,
              help="Print duplicate group count and wasted space, then exit")
@click.option("--json", "out_json", default=None,
              help="Export results to a JSON file")
@click.option("--csv",  "out_csv",  default=None,
              help="Export results to a CSV file")
@click.option("--html", "out_html", default=None,
              help="Export a self-contained HTML report (open in browser)")
def scan(paths, min_size, max_size, types, exclude, pattern,
         summary, count, out_json, out_csv, out_html):
    """Scan folders and list all duplicate files."""
    norm_types = _normalise_types(types)
    console.print(f"\n[bold]dupegun[/bold] — scanning {len(paths)} path(s)...\n")
    groups = _scan(paths, min_size, max_size, norm_types, set(exclude), pattern)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if count:
        print_count(groups)
        return

    if summary:
        print_summary(groups)
    else:
        print_table(groups)

    if out_json:
        export_json(groups, out_json)
    if out_csv:
        export_csv(groups, out_csv)
    if out_html:
        export_html(groups, out_html)

# ── stats ─────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@_common_scan_opts
def stats(paths, min_size, max_size, types, exclude, pattern):
    """Show folder statistics: total files, size, duplicate count, wasted space.

    \b
    Example:
        dupegun stats ~/Downloads
    """
    norm_types = _normalise_types(types)
    min_b      = _parse_size(min_size) if isinstance(min_size, str) else min_size
    max_b      = _parse_size(max_size) if max_size else None
    roots      = [Path(p) for p in paths]

    console.print(f"\n[bold]dupegun stats[/bold] — analysing {len(paths)} path(s)...\n")

    # Collect all files (unfiltered by dedup) for the total-files count
    all_files = [
        f for root in roots
        for f in walk_files(
            root,
            min_size=min_b,
            max_size=max_b,
            types=norm_types,
            exclude=set(exclude),
            pattern=pattern,
        )
    ]

    # Then find duplicates in the same set
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Hashing...", total=None)

        def cb(done, total, path):
            progress.update(
                task, completed=done, total=total,
                description=f"Hashing [cyan]{path.name}[/cyan]",
            )

        groups = find_duplicates(
            roots,
            min_size=min_b,
            max_size=max_b,
            progress_cb=cb,
            types=norm_types,
            exclude=set(exclude),
            pattern=pattern,
        )

    print_stats(roots, groups, all_files)

# ── compare ───────────────────────────────────────────────────────────────────

@main.command()
@click.argument("path_a", type=click.Path(exists=True))
@click.argument("path_b", type=click.Path(exists=True))
@click.option("--min-size", default="1",
              help="Minimum file size (e.g. 1, 500B, 1KB, 1MB). Default: 1")
@click.option("--max-size", default=None,
              help="Maximum file size (e.g. 100MB, 2GB). Default: no limit")
@click.option("--type", "types", multiple=True, metavar="EXT",
              help="Only compare files with this extension (repeatable)")
@click.option("--exclude", multiple=True, metavar="NAME",
              help="Skip folders with this name (repeatable)")
@click.option("--pattern", default=None, metavar="REGEX",
              help="Only compare filenames matching this regex")
def compare(path_a, path_b, min_size, max_size, types, exclude, pattern):
    """Compare two folders and show files duplicated across both.

    \b
    Example:
        dupegun compare ~/Downloads ~/Backup
    """
    norm_types = _normalise_types(types)
    min_b      = _parse_size(min_size) if isinstance(min_size, str) else min_size
    max_b      = _parse_size(max_size) if max_size else None

    console.print(
        f"\n[bold]dupegun compare[/bold] — "
        f"[cyan]{path_a}[/cyan]  ↔  [cyan]{path_b}[/cyan]\n"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Comparing...", total=None)

        def cb(done, total, path):
            progress.update(
                task, completed=done, total=total,
                description=f"Hashing [cyan]{path.name}[/cyan]",
            )

        cross = find_cross_duplicates(
            Path(path_a), Path(path_b),
            min_size=min_b,
            max_size=max_b,
            types=norm_types,
            exclude=set(exclude),
            pattern=pattern,
            progress_cb=cb,
        )

    print_comparison(cross, path_a, path_b)

# ── delete ────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--strategy", default="shortest",
              type=click.Choice(["shortest", "newest", "oldest"]),
              help="Which copy to keep (default: shortest path)")
@click.option("--dry-run/--no-dry-run", default=True,
              help="Preview without deleting (default: ON)")
@click.option("--interactive", is_flag=True,
              help="Confirm each group before deleting")
@click.option("--older-than", default=None, type=int, metavar="DAYS",
              help="Only delete copies older than this many days")
@click.option("--log", "log_path", default=None, metavar="FILE",
              help="Save a TSV log of every deleted file to this path")
@_common_scan_opts
def delete(paths, strategy, dry_run, interactive, older_than, log_path,
           min_size, max_size, types, exclude, pattern):
    """Delete duplicates, keeping one copy per group."""
    norm_types = _normalise_types(types)
    groups = _scan(paths, min_size, max_size, norm_types, set(exclude), pattern)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if dry_run:
        console.print(
            "[yellow]DRY RUN — nothing will be deleted. "
            "Use --no-dry-run to actually delete.[/yellow]\n"
        )

    if older_than:
        console.print(
            f"[dim]--older-than {older_than}: only deleting copies "
            f"last modified more than {older_than} day(s) ago.[/dim]\n"
        )

    delete_dupes(
        groups,
        strategy=strategy,
        dry_run=dry_run,
        interactive=interactive,
        older_than=older_than,
        log_path=log_path,
    )

# ── move ──────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--dest", required=True,
              help="Destination folder to move duplicates into")
@click.option("--strategy", default="shortest",
              type=click.Choice(["shortest", "newest", "oldest"]))
@click.option("--dry-run/--no-dry-run", default=True)
@_common_scan_opts
def move(paths, dest, strategy, dry_run,
         min_size, max_size, types, exclude, pattern):
    """Move duplicates to a quarantine folder instead of deleting."""
    norm_types = _normalise_types(types)
    groups = _scan(paths, min_size, max_size, norm_types, set(exclude), pattern)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if dry_run:
        console.print(
            "[yellow]DRY RUN — nothing will be moved. "
            "Use --no-dry-run to actually move.[/yellow]\n"
        )

    move_dupes(groups, Path(dest), strategy=strategy, dry_run=dry_run)

# ── hardlink ──────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--strategy", default="shortest",
              type=click.Choice(["shortest", "newest", "oldest"]))
@click.option("--dry-run/--no-dry-run", default=True)
@_common_scan_opts
def hardlink(paths, strategy, dry_run,
             min_size, max_size, types, exclude, pattern):
    """Replace duplicates with hard links to save space."""
    norm_types = _normalise_types(types)
    groups = _scan(paths, min_size, max_size, norm_types, set(exclude), pattern)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if dry_run:
        console.print(
            "[yellow]DRY RUN — nothing will be changed. "
            "Use --no-dry-run to actually hardlink.[/yellow]\n"
        )

    hardlink_dupes(groups, strategy=strategy, dry_run=dry_run)
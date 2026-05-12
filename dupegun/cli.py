import click
from pathlib import Path
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn,
    TextColumn, BarColumn, TaskProgressColumn
)

from .scanner import find_duplicates
from .reporter import print_table, export_json, export_csv
from .actions import delete_dupes, move_dupes, hardlink_dupes

console = Console()

def _scan(paths, min_size):
    roots = [Path(p) for p in paths]
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
                description=f"Hashing [cyan]{path.name}[/cyan]"
            )
        groups = find_duplicates(roots, min_size=min_size, progress_cb=cb)
    return groups

@click.group()
@click.version_option("1.0.0", prog_name="dupegun")
def main():
    """dupegun — find and destroy duplicate files.

    Works on Windows, Linux and macOS. All file types supported.
    """
    pass

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--min-size", default=1,
              help="Minimum file size in bytes to scan (default: 1)")
@click.option("--json", "out_json", default=None,
              help="Export results to a JSON file")
@click.option("--csv", "out_csv", default=None,
              help="Export results to a CSV file")
def scan(paths, min_size, out_json, out_csv):
    """Scan folders and list all duplicate files."""
    console.print(f"\n[bold]dupegun[/bold] — scanning {len(paths)} path(s)...\n")
    groups = _scan(paths, min_size)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    print_table(groups)

    if out_json:
        export_json(groups, out_json)
    if out_csv:
        export_csv(groups, out_csv)

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
@click.option("--min-size", default=1)
def delete(paths, strategy, dry_run, interactive, min_size):
    """Delete duplicates, keeping one copy per group."""
    groups = _scan(paths, min_size)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if dry_run:
        console.print(
            "[yellow]DRY RUN — nothing will be deleted. "
            "Use --no-dry-run to actually delete.[/yellow]\n"
        )

    delete_dupes(
        groups,
        strategy=strategy,
        dry_run=dry_run,
        interactive=interactive
    )

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--dest", required=True,
              help="Destination folder to move duplicates into")
@click.option("--strategy", default="shortest",
              type=click.Choice(["shortest", "newest", "oldest"]))
@click.option("--dry-run/--no-dry-run", default=True)
@click.option("--min-size", default=1)
def move(paths, dest, strategy, dry_run, min_size):
    """Move duplicates to a quarantine folder instead of deleting."""
    groups = _scan(paths, min_size)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if dry_run:
        console.print(
            "[yellow]DRY RUN — nothing will be moved. "
            "Use --no-dry-run to actually move.[/yellow]\n"
        )

    move_dupes(groups, Path(dest), strategy=strategy, dry_run=dry_run)

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--strategy", default="shortest",
              type=click.Choice(["shortest", "newest", "oldest"]))
@click.option("--dry-run/--no-dry-run", default=True)
@click.option("--min-size", default=1)
def hardlink(paths, strategy, dry_run, min_size):
    """Replace duplicates with hard links to save space."""
    groups = _scan(paths, min_size)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if dry_run:
        console.print(
            "[yellow]DRY RUN — nothing will be changed. "
            "Use --no-dry-run to actually hardlink.[/yellow]\n"
        )

    hardlink_dupes(groups, strategy=strategy, dry_run=dry_run)
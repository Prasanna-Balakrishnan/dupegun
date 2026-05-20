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
from .actions import delete_dupes, move_dupes, hardlink_dupes, pick_keeper
from .plugins import load_plugins, list_strategies, get_strategy
from .config import load_config, generate_default_config, config_exists

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


def _merge_config(cfg: dict, **cli_kwargs) -> dict:
    """
    Merge config-file defaults with CLI values.
    CLI values always win (non-None / non-empty beats config).
    """
    merged = dict(cfg)
    for k, v in cli_kwargs.items():
        if v is not None and v != () and v != "1" or k not in merged:
            merged[k] = v
    return merged


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
    """Options shared by scan, delete, move, hardlink, tui, watch."""
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
        help='Only scan filenames matching this regex',
    )(fn)
    return fn


def _plugin_opt(fn):
    return click.option(
        "--plugin", "plugins", multiple=True, metavar="FILE",
        help="Load a plugin .py file (repeatable)",
    )(fn)


def _config_opt(fn):
    return click.option(
        "--config", "config_path", default=None, metavar="FILE",
        help="Path to a config TOML file (default: ~/.dupegun.toml)",
    )(fn)


# ── CLI group ─────────────────────────────────────────────────────────────────

@click.group()
@click.version_option("2.0.0", prog_name="dupegun")
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
@_config_opt
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
def scan(paths, min_size, max_size, types, exclude, pattern, config_path,
         summary, count, out_json, out_csv, out_html):
    """Scan folders and list all duplicate files."""
    cfg = load_config(config_path)
    norm_types = _normalise_types(types or cfg.get("types", ()))
    eff_exclude = set(exclude) | set(cfg.get("exclude", ()))
    eff_min     = min_size if min_size != "1" else cfg.get("min_size", "1")
    eff_max     = max_size or cfg.get("max_size")
    eff_pattern = pattern or cfg.get("pattern")

    console.print(f"\n[bold]dupegun[/bold] — scanning {len(paths)} path(s)...\n")
    groups = _scan(paths, eff_min, eff_max, norm_types, eff_exclude, eff_pattern)

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

# ── tui ───────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@_common_scan_opts
@_plugin_opt
@_config_opt
@click.option("--strategy", default=None,
              help="Which copy to keep by default in the TUI (default: shortest)")
@click.option("--dry-run/--no-dry-run", default=True,
              help="Preview mode — no files are deleted (default: ON)")
def tui(paths, min_size, max_size, types, exclude, pattern,
        plugins, config_path, strategy, dry_run):
    """Browse and delete duplicates in an interactive terminal UI.

    \b
    Controls:
      Space        Toggle file for deletion
      D            Delete all marked files in current group
      A            Mark all duplicates in group (keep first)
      U            Unmark all in group
      S            Skip to next group
      Q / Escape   Quit

    Requires:  pip install textual
    """
    from .tui import run_tui

    cfg = load_config(config_path)
    load_plugins(list(plugins) + cfg.get("plugin_files", []))

    norm_types  = _normalise_types(types or cfg.get("types", ()))
    eff_exclude = set(exclude) | set(cfg.get("exclude", ()))
    eff_min     = min_size if min_size != "1" else cfg.get("min_size", "1")
    eff_max     = max_size or cfg.get("max_size")
    eff_pattern = pattern or cfg.get("pattern")
    eff_strategy = strategy or cfg.get("strategy", "shortest")

    console.print(f"\n[bold]dupegun tui[/bold] — scanning {len(paths)} path(s)...\n")
    groups = _scan(paths, eff_min, eff_max, norm_types, eff_exclude, eff_pattern)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    console.print(
        f"Found [bold]{len(groups)}[/bold] duplicate group(s). "
        f"Launching TUI...\n"
    )
    run_tui(groups, strategy=eff_strategy, dry_run=dry_run)

# ── watch ─────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("path", type=click.Path(exists=True))
@_common_scan_opts
@_config_opt
def watch(path, min_size, max_size, types, exclude, pattern, config_path):
    """Monitor a folder and alert when a duplicate file appears.

    \b
    Press Ctrl+C to stop watching.

    Requires:  pip install watchdog
    """
    from .watcher import run_watch

    cfg = load_config(config_path)
    norm_types  = _normalise_types(types or cfg.get("types", ()))
    eff_exclude = set(exclude) | set(cfg.get("exclude", ()))
    eff_min_str = min_size if min_size != "1" else cfg.get("min_size", "1")
    eff_max_str = max_size or cfg.get("max_size")
    eff_min     = _parse_size(eff_min_str) if isinstance(eff_min_str, str) else eff_min_str
    eff_max     = _parse_size(eff_max_str) if eff_max_str else None

    run_watch(
        Path(path),
        min_size=eff_min,
        max_size=eff_max,
        types=norm_types,
        exclude=eff_exclude,
    )

# ── config ────────────────────────────────────────────────────────────────────

@main.command("config")
@click.option("--init", is_flag=True,
              help="Create a default ~/.dupegun.toml if it doesn't exist")
@click.option("--show", is_flag=True,
              help="Print the current config file contents")
@click.option("--path", "show_path", is_flag=True,
              help="Print the path to the config file")
def config_cmd(init, show, show_path):
    """Manage the dupegun config file (~/.dupegun.toml).

    \b
    Examples:
        dupegun config --init      # create a default config
        dupegun config --show      # print current config
        dupegun config --path      # show where the config lives
    """
    from .config import DEFAULT_CONFIG_PATH

    if show_path:
        console.print(str(DEFAULT_CONFIG_PATH))
        return

    if init:
        if config_exists():
            console.print(
                f"[yellow]Config already exists:[/yellow] {DEFAULT_CONFIG_PATH}"
            )
        else:
            DEFAULT_CONFIG_PATH.write_text(generate_default_config(), encoding="utf-8")
            console.print(
                f"[green]Created config:[/green] {DEFAULT_CONFIG_PATH}"
            )
        return

    if show:
        if not config_exists():
            console.print(
                f"[yellow]No config file found at {DEFAULT_CONFIG_PATH}[/yellow]\n"
                "Run [bold]dupegun config --init[/bold] to create one."
            )
        else:
            console.print(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        return

    # No flag — print help
    ctx = click.get_current_context()
    console.print(ctx.get_help())

# ── stats ─────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@_common_scan_opts
@_config_opt
def stats(paths, min_size, max_size, types, exclude, pattern, config_path):
    """Show folder statistics: total files, size, duplicate count, wasted space."""
    cfg = load_config(config_path)
    norm_types  = _normalise_types(types or cfg.get("types", ()))
    eff_exclude = set(exclude) | set(cfg.get("exclude", ()))
    eff_min_str = min_size if min_size != "1" else cfg.get("min_size", "1")
    eff_max_str = max_size or cfg.get("max_size")
    min_b = _parse_size(eff_min_str) if isinstance(eff_min_str, str) else eff_min_str
    max_b = _parse_size(eff_max_str) if eff_max_str else None
    roots = [Path(p) for p in paths]

    console.print(f"\n[bold]dupegun stats[/bold] — analysing {len(paths)} path(s)...\n")

    all_files = [
        f for root in roots
        for f in walk_files(root, min_size=min_b, max_size=max_b,
                            types=norm_types, exclude=eff_exclude,
                            pattern=pattern or cfg.get("pattern"))
    ]

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), TaskProgressColumn(), transient=True) as progress:
        task = progress.add_task("Hashing...", total=None)
        def cb(done, total, path):
            progress.update(task, completed=done, total=total,
                            description=f"Hashing [cyan]{path.name}[/cyan]")
        groups = find_duplicates(roots, min_size=min_b, max_size=max_b,
                                 progress_cb=cb, types=norm_types,
                                 exclude=eff_exclude,
                                 pattern=pattern or cfg.get("pattern"))

    print_stats(roots, groups, all_files)

# ── compare ───────────────────────────────────────────────────────────────────

@main.command()
@click.argument("path_a", type=click.Path(exists=True))
@click.argument("path_b", type=click.Path(exists=True))
@click.option("--min-size", default="1")
@click.option("--max-size", default=None)
@click.option("--type", "types", multiple=True, metavar="EXT")
@click.option("--exclude", multiple=True, metavar="NAME")
@click.option("--pattern", default=None, metavar="REGEX")
def compare(path_a, path_b, min_size, max_size, types, exclude, pattern):
    """Compare two folders and show files duplicated across both."""
    norm_types = _normalise_types(types)
    min_b = _parse_size(min_size) if isinstance(min_size, str) else min_size
    max_b = _parse_size(max_size) if max_size else None

    console.print(
        f"\n[bold]dupegun compare[/bold] — "
        f"[cyan]{path_a}[/cyan]  ↔  [cyan]{path_b}[/cyan]\n"
    )

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), TaskProgressColumn(), transient=True) as progress:
        task = progress.add_task("Comparing...", total=None)
        def cb(done, total, path):
            progress.update(task, completed=done, total=total,
                            description=f"Hashing [cyan]{path.name}[/cyan]")
        cross = find_cross_duplicates(
            Path(path_a), Path(path_b), min_size=min_b, max_size=max_b,
            types=norm_types, exclude=set(exclude), pattern=pattern, progress_cb=cb,
        )

    print_comparison(cross, path_a, path_b)

# ── delete ────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--strategy", default=None,
              help="Which copy to keep: shortest|newest|oldest|<plugin> (default: shortest)")
@click.option("--dry-run/--no-dry-run", default=True)
@click.option("--interactive", is_flag=True)
@click.option("--older-than", default=None, type=int, metavar="DAYS")
@click.option("--log", "log_path", default=None, metavar="FILE")
@_common_scan_opts
@_plugin_opt
@_config_opt
def delete(paths, strategy, dry_run, interactive, older_than, log_path,
           min_size, max_size, types, exclude, pattern, plugins, config_path):
    """Delete duplicates, keeping one copy per group."""
    cfg = load_config(config_path)
    load_plugins(list(plugins) + cfg.get("plugin_files", []))

    norm_types  = _normalise_types(types or cfg.get("types", ()))
    eff_exclude = set(exclude) | set(cfg.get("exclude", ()))
    eff_strategy = strategy or cfg.get("strategy", "shortest")

    # Validate strategy (built-in + plugins)
    builtin = {"shortest", "newest", "oldest"}
    if eff_strategy not in builtin and get_strategy(eff_strategy) is None:
        raise click.BadParameter(
            f"Unknown strategy '{eff_strategy}'. "
            f"Built-in: {', '.join(sorted(builtin))}. "
            f"Plugin strategies: {', '.join(list_strategies()) or 'none loaded'}."
        )

    groups = _scan(paths, min_size, max_size, norm_types, eff_exclude, pattern)

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
            f"modified more than {older_than} day(s) ago.[/dim]\n"
        )

    delete_dupes(groups, strategy=eff_strategy, dry_run=dry_run,
                 interactive=interactive, older_than=older_than, log_path=log_path)

# ── move ──────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--dest", required=True)
@click.option("--strategy", default="shortest",
              type=click.Choice(["shortest", "newest", "oldest"]))
@click.option("--dry-run/--no-dry-run", default=True)
@_common_scan_opts
@_config_opt
def move(paths, dest, strategy, dry_run,
         min_size, max_size, types, exclude, pattern, config_path):
    """Move duplicates to a quarantine folder instead of deleting."""
    cfg = load_config(config_path)
    norm_types  = _normalise_types(types or cfg.get("types", ()))
    eff_exclude = set(exclude) | set(cfg.get("exclude", ()))
    groups = _scan(paths, min_size, max_size, norm_types, eff_exclude, pattern)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if dry_run:
        console.print("[yellow]DRY RUN — nothing will be moved.[/yellow]\n")

    move_dupes(groups, Path(dest), strategy=strategy, dry_run=dry_run)

# ── hardlink ──────────────────────────────────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True))
@click.option("--strategy", default="shortest",
              type=click.Choice(["shortest", "newest", "oldest"]))
@click.option("--dry-run/--no-dry-run", default=True)
@_common_scan_opts
@_config_opt
def hardlink(paths, strategy, dry_run,
             min_size, max_size, types, exclude, pattern, config_path):
    """Replace duplicates with hard links to save space."""
    cfg = load_config(config_path)
    norm_types  = _normalise_types(types or cfg.get("types", ()))
    eff_exclude = set(exclude) | set(cfg.get("exclude", ()))
    groups = _scan(paths, min_size, max_size, norm_types, eff_exclude, pattern)

    if not groups:
        console.print("[bold green]No duplicates found![/bold green]")
        return

    if dry_run:
        console.print("[yellow]DRY RUN — nothing will be changed.[/yellow]\n")

    hardlink_dupes(groups, strategy=strategy, dry_run=dry_run)
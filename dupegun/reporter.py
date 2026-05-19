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
        t.add_column("#",        style="dim",    width=4)
        t.add_column("Path",     style="cyan")
        t.add_column("Modified", style="yellow")
        t.add_column("Size",     justify="right")

        for j, p in enumerate(paths, 1):
            stat  = p.stat()
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


def print_comparison(cross: dict, path_a: str, path_b: str) -> None:
    """
    Print a comparison report for `dupegun compare`.

    *cross* is the dict returned by find_cross_duplicates:
        hash -> {'a': [Path, ...], 'b': [Path, ...]}
    """
    if not cross:
        console.print(
            "[bold green]No cross-directory duplicates found![/bold green]"
        )
        return

    total_size = 0
    for i, (h, sides) in enumerate(cross.items(), 1):
        try:
            size = sides["a"][0].stat().st_size
        except (OSError, PermissionError):
            size = 0
        total_size += size

        t = Table(
            title=f"[bold]Match {i}[/bold] — {human_size(size)} each",
            show_lines=True,
        )
        t.add_column("Side",     style="bold magenta", width=6)
        t.add_column("Path",     style="cyan")
        t.add_column("Modified", style="yellow")

        for p in sides["a"]:
            try:
                mtime = datetime.datetime.fromtimestamp(
                    p.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M")
            except (OSError, PermissionError):
                mtime = "—"
            t.add_row("A", str(p), mtime)

        for p in sides["b"]:
            try:
                mtime = datetime.datetime.fromtimestamp(
                    p.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M")
            except (OSError, PermissionError):
                mtime = "—"
            t.add_row("B", str(p), mtime)

        console.print(t)

    console.print(
        f"\n[bold yellow]{len(cross)}[/bold yellow] file(s) duplicated between "
        f"[cyan]{path_a}[/cyan] and [cyan]{path_b}[/cyan]  "
        f"([red]{human_size(total_size)} redundant[/red])\n"
    )


def print_stats(roots: list, groups: dict, all_files: list) -> None:
    """
    Print a folder statistics summary for `dupegun stats`.

    Args:
        roots:     The scanned root paths.
        groups:    Duplicate groups from find_duplicates.
        all_files: Flat list of every file found (before dedup filtering).
    """
    total_files = len(all_files)
    try:
        total_size = sum(p.stat().st_size for p in all_files)
    except (OSError, PermissionError):
        total_size = 0

    wasted      = _wasted(groups)
    pct         = (wasted / total_size * 100) if total_size else 0.0
    dup_groups  = len(groups)
    dup_files   = sum(len(paths) for paths in groups.values())

    t = Table(show_header=False, show_lines=False, box=None, padding=(0, 2))
    t.add_column("Label", style="bold")
    t.add_column("Value", justify="right")

    t.add_row("Scanned paths",    ", ".join(str(r) for r in roots))
    t.add_row("Total files",      f"{total_files:,}")
    t.add_row("Total size",       human_size(total_size))
    t.add_row("Duplicate groups", f"{dup_groups:,}")
    t.add_row("Duplicate files",  f"{dup_files:,}")
    t.add_row("Wasted space",     f"{human_size(wasted)} ({pct:.1f}%)")

    console.print()
    console.print(t)
    console.print()


def export_html(groups: dict, out_path: str) -> None:
    """
    Generate a self-contained HTML report of all duplicate groups.
    Opens cleanly in any browser — no external dependencies.
    """
    now    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    wasted = _wasted(groups)

    # Build group rows
    group_rows = []
    for i, (h, paths) in enumerate(groups.items(), 1):
        try:
            size   = paths[0].stat().st_size
        except (OSError, PermissionError):
            size = 0
        grp_wasted = size * (len(paths) - 1)

        file_rows = []
        for j, p in enumerate(paths, 1):
            try:
                stat  = p.stat()
                mtime = datetime.datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%Y-%m-%d %H:%M")
                fsize = human_size(stat.st_size)
            except (OSError, PermissionError):
                mtime = "—"
                fsize = "—"
            file_rows.append(
                f"<tr>"
                f"<td class='num'>{j}</td>"
                f"<td class='path'>{p}</td>"
                f"<td>{mtime}</td>"
                f"<td class='num'>{fsize}</td>"
                f"</tr>"
            )

        group_rows.append(f"""
        <div class="group">
          <div class="group-header">
            <span class="group-title">Group {i}</span>
            <span class="group-meta">{human_size(size)} each &mdash;
              <span class="wasted">{human_size(grp_wasted)} wasted</span>
              &mdash; {len(paths)} files</span>
            <span class="hash">SHA-256: {h[:16]}…</span>
          </div>
          <table>
            <thead>
              <tr><th>#</th><th>Path</th><th>Modified</th><th>Size</th></tr>
            </thead>
            <tbody>
              {"".join(file_rows)}
            </tbody>
          </table>
        </div>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>dupegun report — {now}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, sans-serif;
      background: #0f1117;
      color: #e2e8f0;
      padding: 2rem;
      line-height: 1.5;
    }}
    header {{
      margin-bottom: 2rem;
      border-bottom: 1px solid #2d3748;
      padding-bottom: 1rem;
    }}
    header h1 {{ font-size: 1.8rem; color: #63b3ed; }}
    header p  {{ color: #a0aec0; font-size: 0.9rem; margin-top: 0.25rem; }}
    .summary {{
      display: flex; gap: 1.5rem; flex-wrap: wrap;
      margin-bottom: 2rem;
    }}
    .stat-card {{
      background: #1a202c; border: 1px solid #2d3748;
      border-radius: 8px; padding: 1rem 1.5rem; min-width: 160px;
    }}
    .stat-card .label {{ font-size: 0.75rem; color: #a0aec0; text-transform: uppercase; }}
    .stat-card .value {{ font-size: 1.4rem; font-weight: 700; color: #f6e05e; margin-top: 2px; }}
    .group {{
      background: #1a202c; border: 1px solid #2d3748;
      border-radius: 8px; margin-bottom: 1.25rem; overflow: hidden;
    }}
    .group-header {{
      display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
      padding: 0.75rem 1rem; background: #2d3748;
    }}
    .group-title {{ font-weight: 700; color: #90cdf4; font-size: 0.95rem; }}
    .group-meta  {{ font-size: 0.85rem; color: #a0aec0; }}
    .wasted      {{ color: #fc8181; font-weight: 600; }}
    .hash        {{ font-size: 0.75rem; color: #4a5568; font-family: monospace; margin-left: auto; }}
    table  {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    thead  {{ background: #171923; }}
    th     {{ padding: 0.5rem 1rem; text-align: left; color: #718096;
              font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }}
    td     {{ padding: 0.5rem 1rem; border-top: 1px solid #2d3748; }}
    td.path  {{ font-family: monospace; word-break: break-all; color: #76e4f7; }}
    td.num   {{ text-align: right; color: #a0aec0; white-space: nowrap; }}
    tr:hover td {{ background: #2d3748; }}
    footer {{ margin-top: 2rem; color: #4a5568; font-size: 0.8rem; text-align: center; }}
  </style>
</head>
<body>
  <header>
    <h1>dupegun report</h1>
    <p>Generated {now} &mdash; {len(groups)} duplicate group(s) &mdash;
       {human_size(wasted)} reclaimable</p>
  </header>

  <div class="summary">
    <div class="stat-card">
      <div class="label">Duplicate groups</div>
      <div class="value">{len(groups)}</div>
    </div>
    <div class="stat-card">
      <div class="label">Wasted space</div>
      <div class="value">{human_size(wasted)}</div>
    </div>
    <div class="stat-card">
      <div class="label">Total duplicate files</div>
      <div class="value">{sum(len(p) for p in groups.values())}</div>
    </div>
  </div>

  {"".join(group_rows)}

  <footer>dupegun &mdash; <a href="https://github.com/Prasanna-Balakrishnan/dupegun"
    style="color:#4a5568">github.com/Prasanna-Balakrishnan/dupegun</a></footer>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    console.print(f"[green]HTML report → {out_path}[/green]")


def export_json(groups: dict, out_path: str) -> None:
    data = [
        {
            "hash":      h,
            "count":     len(paths),
            "size_each": paths[0].stat().st_size,
            "files":     [str(p) for p in paths],
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
                stat  = p.stat()
                mtime = datetime.datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%Y-%m-%d %H:%M")
                w.writerow([i, h, str(p), stat.st_size, mtime])
    console.print(f"[green]Exported CSV → {out_path}[/green]")
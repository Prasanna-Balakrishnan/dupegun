"""
dupegun TUI browser
====================

An interactive terminal UI for browsing and deleting duplicate groups.

Controls
--------
    Arrow keys / j k   Navigate between files
    Tab / Shift+Tab     Move between groups
    Space               Toggle file selection (mark for deletion)
    D                   Delete all marked files in the current group
    A                   Select all duplicates in current group (keep first)
    U                   Unselect all in current group
    S                   Skip to next group
    Q / Escape          Quit

Requires the `textual` library:
    pip install textual
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .reporter import human_size
from .actions import pick_keeper

# ── Textual import guard ──────────────────────────────────────────────────────

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.widgets import (
        Header, Footer, DataTable, Label, Static
    )
    from textual.containers import Vertical, Horizontal
    from textual.screen import Screen
    from textual import events
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False


def _check_textual() -> None:
    if not _TEXTUAL_AVAILABLE:
        raise SystemExit(
            "\n[dupegun] The TUI requires the 'textual' library.\n"
            "Install it with:  pip install textual\n"
        )


# ── TUI App ───────────────────────────────────────────────────────────────────

if _TEXTUAL_AVAILABLE:

    class DupeGroup:
        """Holds one duplicate group and tracks which files are marked."""

        def __init__(self, hash_val: str, paths: List[Path], strategy: str = "shortest"):
            self.hash_val = hash_val
            self.paths    = paths
            self.keeper   = pick_keeper(paths, strategy)
            # All non-keeper files are marked for deletion by default
            self.marked: set[Path] = {p for p in paths if p != self.keeper}

        @property
        def size(self) -> int:
            try:
                return self.paths[0].stat().st_size
            except (OSError, PermissionError):
                return 0

        @property
        def wasted(self) -> int:
            return self.size * len(self.marked)


    class GroupPanel(Static):
        """Displays one duplicate group with file rows."""

        def __init__(self, group: DupeGroup, group_idx: int, **kwargs):
            super().__init__(**kwargs)
            self.group     = group
            self.group_idx = group_idx

        def compose(self) -> ComposeResult:
            g = self.group
            yield Label(
                f"[bold cyan]Group {self.group_idx + 1}[/bold cyan]  "
                f"{human_size(g.size)} each  |  "
                f"[red]{human_size(g.wasted)} wasted[/red]  |  "
                f"{len(g.paths)} files"
            )
            table = DataTable(id=f"table_{self.group_idx}")
            table.add_columns("Status", "Path", "Size", "Modified")
            self._table = table
            yield table

        def on_mount(self) -> None:
            self._refresh_rows()

        def _refresh_rows(self) -> None:
            import datetime
            table = self.query_one(DataTable)
            table.clear()
            for p in self.group.paths:
                try:
                    stat  = p.stat()
                    size  = human_size(stat.st_size)
                    mtime = datetime.datetime.fromtimestamp(
                        stat.st_mtime
                    ).strftime("%Y-%m-%d %H:%M")
                except (OSError, PermissionError):
                    size  = "—"
                    mtime = "—"

                if p == self.group.keeper:
                    status = "[green]KEEP[/green]"
                elif p in self.group.marked:
                    status = "[red]DELETE[/red]"
                else:
                    status = "[dim]skip[/dim]"

                table.add_row(status, str(p), size, mtime)

        def toggle(self, row_idx: int) -> None:
            p = self.group.paths[row_idx]
            if p == self.group.keeper:
                return  # cannot mark the keeper
            if p in self.group.marked:
                self.group.marked.discard(p)
            else:
                self.group.marked.add(p)
            self._refresh_rows()

        def select_all(self) -> None:
            self.group.marked = {p for p in self.group.paths if p != self.group.keeper}
            self._refresh_rows()

        def unselect_all(self) -> None:
            self.group.marked.clear()
            self._refresh_rows()


    class DupegunTUI(App):
        """Main TUI application."""

        CSS = """
        Screen {
            layout: vertical;
        }
        GroupPanel {
            border: solid $primary-darken-2;
            margin: 1 0;
            padding: 0 1;
        }
        DataTable {
            height: auto;
            max-height: 12;
        }
        #status_bar {
            background: $surface;
            padding: 0 1;
            height: 1;
        }
        """

        BINDINGS = [
            Binding("q",      "quit",        "Quit"),
            Binding("escape", "quit",        "Quit", show=False),
            Binding("space",  "toggle",      "Toggle"),
            Binding("d",      "delete_group","Delete marked"),
            Binding("a",      "select_all",  "Select all"),
            Binding("u",      "unselect",    "Unselect all"),
            Binding("s",      "skip",        "Skip group"),
        ]

        def __init__(self, groups: Dict[str, List[Path]], strategy: str = "shortest",
                     dry_run: bool = True):
            super().__init__()
            self.dupe_groups = [
                DupeGroup(h, paths, strategy)
                for h, paths in groups.items()
            ]
            self.dry_run      = dry_run
            self.current_idx  = 0
            self.total_freed  = 0

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical():
                for i, g in enumerate(self.dupe_groups):
                    yield GroupPanel(g, i, id=f"group_{i}")
                yield Static("", id="status_bar")
            yield Footer()

        def on_mount(self) -> None:
            self._update_status()

        def _current_panel(self) -> GroupPanel | None:
            panels = self.query(GroupPanel)
            if not panels or self.current_idx >= len(panels):
                return None
            return list(panels)[self.current_idx]

        def _update_status(self) -> None:
            total_marked = sum(len(g.marked) for g in self.dupe_groups)
            total_wasted = sum(g.wasted for g in self.dupe_groups)
            mode = "[yellow]DRY RUN[/yellow]" if self.dry_run else "[red]LIVE[/red]"
            self.query_one("#status_bar", Static).update(
                f"{mode}  |  "
                f"Group {self.current_idx + 1}/{len(self.dupe_groups)}  |  "
                f"{total_marked} file(s) marked  |  "
                f"{human_size(total_wasted)} to free"
            )

        def action_toggle(self) -> None:
            panel = self._current_panel()
            if panel is None:
                return
            table = panel.query_one(DataTable)
            if table.cursor_row is not None:
                panel.toggle(table.cursor_row)
            self._update_status()

        def action_select_all(self) -> None:
            panel = self._current_panel()
            if panel:
                panel.select_all()
                self._update_status()

        def action_unselect(self) -> None:
            panel = self._current_panel()
            if panel:
                panel.unselect_all()
                self._update_status()

        def action_skip(self) -> None:
            if self.current_idx < len(self.dupe_groups) - 1:
                self.current_idx += 1
                self._update_status()

        def action_delete_group(self) -> None:
            panel = self._current_panel()
            if panel is None:
                return
            group = panel.group
            for p in list(group.marked):
                if self.dry_run:
                    self.notify(f"[DRY RUN] would delete {p.name}", severity="warning")
                else:
                    try:
                        size = p.stat().st_size
                        p.unlink()
                        self.total_freed += size
                        group.marked.discard(p)
                        self.notify(f"Deleted {p.name}", severity="information")
                    except OSError as e:
                        self.notify(f"Error: {e}", severity="error")
            panel._refresh_rows()
            self._update_status()

        def action_quit(self) -> None:
            freed = human_size(self.total_freed)
            self.exit(message=freed)


# ── public entry point ────────────────────────────────────────────────────────

def run_tui(groups: Dict[str, List[Path]], strategy: str = "shortest",
            dry_run: bool = True) -> None:
    """
    Launch the interactive TUI browser.

    Args:
        groups:   Hash -> [Path, ...] from find_duplicates.
        strategy: Which file to mark as KEEP by default.
        dry_run:  If True, deletions are previewed only.
    """
    _check_textual()
    app = DupegunTUI(groups, strategy=strategy, dry_run=dry_run)
    result = app.run()
    if result:
        print(f"\nTotal freed: {result}")
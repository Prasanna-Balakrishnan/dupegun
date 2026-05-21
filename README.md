# dupegun

> A fast, cross-platform command-line tool to find and eliminate duplicate files.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![PyPI](https://img.shields.io/pypi/v/dupegun.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

---

## What is dupegun?

**dupegun** scans your folders, detects duplicate files using a fast 3-pass hashing engine, and lets you delete, move, or hard-link them — all from your terminal. It works on every file type and every major operating system.

No GUI. No bloat. Just fast, safe, and simple.

---

## Install

```bash
# Core install
pip install dupegun

# With TUI browser
pip install "dupegun[tui]"

# With watch mode
pip install "dupegun[watch]"

# Everything
pip install "dupegun[all]"
```

Requires Python 3.9 or higher.

---

## Quick Start

```bash
# Scan a folder and see all duplicates
dupegun scan ~/Downloads

# Interactive TUI browser
dupegun tui ~/Downloads

# Monitor a folder for new duplicates
dupegun watch ~/Downloads

# Preview what would be deleted with a per-group breakdown
dupegun delete ~/Downloads --strategy newest

# Actually delete duplicates and save a log
dupegun delete ~/Downloads --strategy newest --no-dry-run --log deleted.log

# Undo those deletions
dupegun restore deleted.log --no-dry-run
```

---

## Commands

### `scan` — find duplicates

```bash
dupegun scan <path> [options]
```

```bash
# Scan a single folder
dupegun scan ~/Downloads

# Scan multiple folders at once
dupegun scan ~/Downloads ~/Documents ~/Desktop

# Skip files smaller than 1 MB
dupegun scan ~/Downloads --min-size 1MB

# Scan specific size ranges
dupegun scan ~/Downloads --min-size 1MB --max-size 100MB

# Regex filename filter
dupegun scan ~/Downloads --pattern "Copy of.*"

# Only scan image files
dupegun scan ~/Downloads --type .jpg --type .png --type .gif

# Skip specific folders
dupegun scan C:\ --exclude Windows --exclude "Program Files"

# Just show total wasted space
dupegun scan ~/Downloads --summary

# Show count with colorized bar showing % of wasted space
dupegun scan ~/Downloads --count

# Export results
dupegun scan ~/Downloads --json results.json
dupegun scan ~/Downloads --csv results.csv
dupegun scan ~/Downloads --html report.html
```

---

### `restore` — undo deletions

Reverse a previous `dupegun delete --log` run by copying the kept file
back to where each deleted duplicate used to live.

```bash
dupegun restore <log_file> [options]
```

```bash
# Preview what would be restored (dry-run ON by default)
dupegun restore deleted.log

# Actually restore
dupegun restore deleted.log --no-dry-run
```

The restore command reads the TSV log file, shows you exactly what it will
do in a table, then copies the keeper to each deleted path.

---

### `tui` — interactive terminal browser

```bash
# Requires: pip install "dupegun[tui]"
dupegun tui ~/Downloads
dupegun tui ~/Downloads --strategy newest
dupegun tui ~/Downloads --no-dry-run
```

**Controls:**

| Key | Action |
|---|---|
| Space | Toggle file for deletion |
| A | Mark all duplicates in group |
| U | Unmark all in group |
| D | Delete all marked files |
| S | Skip to next group |
| Q / Escape | Quit |

---

### `watch` — monitor for new duplicates

```bash
# Requires: pip install "dupegun[watch]"
dupegun watch ~/Downloads
dupegun watch ~/Photos --type .jpg --type .png
```

Press **Ctrl+C** to stop.

---

### `config` — manage your config file

```bash
dupegun config --init    # create ~/.dupegun.toml
dupegun config --show    # print current config
dupegun config --path    # show config file path
```

**Example `~/.dupegun.toml`:**

```toml
[defaults]
strategy = "newest"
min_size = "100KB"
exclude  = ["node_modules", ".git", "Windows"]

[plugins]
load = ["~/my_plugin.py"]
```

---

### `stats` — folder statistics

```bash
dupegun stats ~/Downloads
```

Output:
```
Scanned paths     ~/Downloads
Total files       1,243
Total size        45.2 GB
Duplicate groups  87
Duplicate files   201
Wasted space      8.3 GB (18.4%)
```

---

### `compare` — cross-directory duplicates

```bash
dupegun compare ~/Downloads ~/Backup
dupegun compare ~/Photos ~/Backup/Photos --type .jpg --type .png
```

---

### `delete` — remove duplicates

```bash
# Preview with detailed per-group breakdown (dry-run ON by default)
dupegun delete ~/Downloads --strategy newest

# Actually delete
dupegun delete ~/Downloads --strategy newest --no-dry-run

# Delete with log so you can restore later
dupegun delete ~/Downloads --no-dry-run --log deleted.log

# Restore if you change your mind
dupegun restore deleted.log --no-dry-run
```

---

### `move` — quarantine duplicates

```bash
dupegun move ~/Downloads --dest ~/quarantine --no-dry-run
```

---

### `hardlink` — save space, keep all paths

```bash
dupegun hardlink ~/Photos --no-dry-run
```

---

## Plugin system

```python
# my_plugin.py
from dupegun.plugins import register_strategy

@register_strategy("by_name")
def keep_alphabetically(paths):
    return min(paths, key=lambda p: p.name.lower())
```

```bash
dupegun delete ~/Downloads --plugin my_plugin.py --strategy by_name --no-dry-run
```

---

## Options

| Option | Commands | Description | Default |
|---|---|---|---|
| `--strategy <name>` | delete, move, hardlink, tui | shortest, newest, oldest, or plugin name | shortest |
| `--dry-run` | delete, move, hardlink, tui | Preview with per-group breakdown | ON |
| `--no-dry-run` | delete, move, hardlink, tui | Actually perform the action | — |
| `--interactive` | delete | Confirm each group before acting | OFF |
| `--older-than <days>` | delete | Only delete copies older than N days | — |
| `--log <file>` | delete | Append a TSV log of every deleted file | — |
| `--plugin <file>` | delete, tui | Load a plugin .py file (repeatable) | — |
| `--config <file>` | all | Path to a TOML config file | ~/.dupegun.toml |
| `--min-size <size>` | all | Skip files smaller than this | 1 byte |
| `--max-size <size>` | all | Skip files larger than this | no limit |
| `--pattern <regex>` | all | Only scan filenames matching this regex | none |
| `--type <ext>` | all | Only include files with this extension (repeatable) | all |
| `--exclude <name>` | all | Skip folders with this name (repeatable) | none |
| `--summary` | scan | Total wasted space only, no file list | OFF |
| `--count` | scan | Group count with colorized wasted-space bar | OFF |
| `--json <file>` | scan | Export results to JSON | — |
| `--csv <file>` | scan | Export results to CSV | — |
| `--html <file>` | scan | Export self-contained HTML report | — |

---

## How it works

```
Pass 1 — Group files by exact byte size
Pass 2 — Hash the first 4 KB of each size-match
Pass 3 — Full SHA-256 hash of remaining candidates
```

---

## Safety

- Dry-run is **ON by default** on every destructive command.
- Dry-run now shows a **per-group breakdown** of exactly what would be freed.
- Use `--log` to keep an audit trail, and `restore` to undo if needed.
- Use `move` instead of `delete` if you want a safety net.

---

## Platform support

| Platform | Supported |
|---|---|
| Windows | Yes |
| Linux | Yes |
| macOS | Yes |

---

## Changelog

### v2.1.0
- **`restore` command**: Undo deletions recorded in a `--log` file. Copies the kept file back to where each deleted duplicate used to live.
- **Dry-run summary**: `delete` dry-run now shows a per-group breakdown — which file would be kept, how many deleted, and exactly how much space would be freed.
- **ETA progress bar**: All scan/hash operations now show estimated time remaining alongside the progress bar.
- **Colorized `--count`**: `scan --count` now shows a color-coded bar (green/yellow/red) indicating what percentage of your total disk usage is wasted on duplicates.

### v2.0.0
- **`tui` command**: Interactive terminal UI browser.
- **`watch` command**: Monitor folders for new duplicates in real time.
- **`config` command**: Manage `~/.dupegun.toml` config file.
- **Plugin system**: Register custom keep-strategies with `@register_strategy`.

### v1.3.0
- **`stats` command**, **`--html`** report, **`--log`** audit trail.

### v1.2.0
- **`compare`** command, **`--older-than`**, **`--max-size`**, **`--pattern`**.

### v1.1.0
- **`--type`**, **`--exclude`**, **`--summary`**, **`--count`**.

### v1.0.0
- Initial release: `scan`, `delete`, `move`, `hardlink`.

---

## Contributing

```bash
git clone https://github.com/Prasanna-Balakrishnan/dupegun.git
cd dupegun
pip install -e ".[all]"
pip install pytest
python -m pytest tests/ -v
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Author

Made by **Prasanna B**

GitHub: https://github.com/Prasanna-Balakrishnan/dupegun

If this tool helped you, consider giving it a star on GitHub!
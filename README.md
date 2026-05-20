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

# Preview what would be deleted (nothing actually deleted)
dupegun delete ~/Downloads --strategy newest

# Actually delete duplicates
dupegun delete ~/Downloads --strategy newest --no-dry-run
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

# Scan specific size ranges (e.g., between 1MB and 100MB)
dupegun scan ~/Downloads --min-size 1MB --max-size 100MB

# Regex filename filter (e.g., files starting with "Copy of")
dupegun scan ~/Downloads --pattern "Copy of.*"

# Only scan image files
dupegun scan ~/Downloads --type .jpg --type .png --type .gif

# Only scan video files
dupegun scan ~/Downloads --type .mp4 --type .mkv --type .avi

# Skip specific folders
dupegun scan C:\ --exclude Windows --exclude "Program Files"

# Just show total wasted space — no file list
dupegun scan ~/Downloads --summary

# Show only the duplicate count and wasted space
dupegun scan ~/Downloads --count

# Export results to JSON
dupegun scan ~/Downloads --json results.json

# Export results to CSV
dupegun scan ~/Downloads --csv results.csv

# Generate a self-contained HTML report you can open in any browser
dupegun scan ~/Downloads --html report.html

# Use settings from a custom config file
dupegun scan ~/Downloads --config ~/myconfig.toml
```

---

### `tui` — interactive terminal browser

Browse duplicates visually, mark files for deletion, and act — all from your keyboard.

```bash
# Requires: pip install "dupegun[tui]"
dupegun tui ~/Downloads
dupegun tui ~/Downloads --strategy newest
dupegun tui ~/Downloads --no-dry-run   # actually delete (default is dry-run)
```

**Controls:**

| Key | Action |
|---|---|
| Arrow keys / j k | Navigate files |
| Space | Toggle file for deletion |
| A | Mark all duplicates in group (keep first) |
| U | Unmark all in group |
| D | Delete all marked files in current group |
| S | Skip to next group |
| Q / Escape | Quit |

---

### `watch` — monitor for new duplicates

Watch a folder in real time and get an alert whenever a duplicate file appears.

```bash
# Requires: pip install "dupegun[watch]"
dupegun watch ~/Downloads

# Watch only for duplicate images
dupegun watch ~/Photos --type .jpg --type .png

# Watch and skip cache folders
dupegun watch ~/Projects --exclude node_modules --exclude .git
```

Press **Ctrl+C** to stop watching.

---

### `config` — manage your config file

Save your preferred settings so you don't type them every time.

```bash
# Create a default ~/.dupegun.toml
dupegun config --init

# Print current config
dupegun config --show

# Show the config file path
dupegun config --path
```

**Example `~/.dupegun.toml`:**

```toml
[defaults]
strategy = "newest"
min_size = "100KB"
exclude  = ["node_modules", ".git", "Windows", "Program Files"]

[plugins]
load = ["~/my_plugin.py"]
```

All CLI flags still override config values.

---

### `stats` — folder statistics

Get a quick overview of a folder: total files, total size, duplicate groups, and how much space is wasted.

```bash
dupegun stats <path> [options]
```

```bash
# Basic stats for a folder
dupegun stats ~/Downloads

# Stats for images only
dupegun stats ~/Photos --type .jpg --type .png

# Stats excluding system folders
dupegun stats C:\ --exclude Windows --exclude "Program Files"
```

Output example:
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

Find files that exist in *both* folders by content, not by name. Great for checking what your backup has in common with your active drive.

```bash
dupegun compare <path_a> <path_b> [options]
```

```bash
# Find files duplicated between Downloads and a Backup drive
dupegun compare ~/Downloads ~/Backup

# Compare only images
dupegun compare ~/Photos /Volumes/Backup/Photos --type .jpg --type .png

# Compare and skip cache folders
dupegun compare ~/Projects ~/Backup --exclude node_modules --exclude .git
```

---

### `delete` — remove duplicates

```bash
dupegun delete <path> [options]
```

```bash
# Preview (dry-run is ON by default — nothing deleted)
dupegun delete ~/Downloads --strategy newest

# Actually delete
dupegun delete ~/Downloads --strategy newest --no-dry-run

# Confirm each group one by one before deleting
dupegun delete ~/Downloads --no-dry-run --interactive

# Auto-delete by age (only delete copies older than 30 days)
dupegun delete ~/Downloads --older-than 30 --no-dry-run

# Delete only duplicate images, skip cache folders
dupegun delete ~/Photos --type .jpg --type .png --exclude .thumbnails --no-dry-run

# Save a log of everything deleted
dupegun delete ~/Downloads --no-dry-run --log deleted.log

# Use a plugin strategy
dupegun delete ~/Downloads --plugin my_plugin.py --strategy by_name --no-dry-run
```

---

### `move` — quarantine duplicates

```bash
dupegun move <path> --dest <quarantine-folder> [options]
```

```bash
# Preview
dupegun move ~/Downloads --dest ~/quarantine

# Actually move
dupegun move ~/Downloads --dest ~/quarantine --no-dry-run
```

---

### `hardlink` — save space, keep all paths

```bash
dupegun hardlink <path> [options]
```

```bash
# Preview
dupegun hardlink ~/Photos

# Actually hardlink
dupegun hardlink ~/Photos --no-dry-run
```

---

## Plugin system

Extend dupegun with custom strategies without touching the core code.

**Create a plugin file:**

```python
# my_plugin.py
from dupegun.plugins import register_strategy

@register_strategy("by_name")
def keep_alphabetically(paths):
    """Keep the file whose name comes first alphabetically."""
    return min(paths, key=lambda p: p.name.lower())

@register_strategy("largest")
def keep_largest(paths):
    """Keep the largest file."""
    return max(paths, key=lambda p: p.stat().st_size)
```

**Use it:**

```bash
dupegun delete ~/Downloads --plugin my_plugin.py --strategy by_name --no-dry-run
```

**Or auto-load via config:**

```toml
# ~/.dupegun.toml
[plugins]
load = ["~/my_plugin.py"]

[defaults]
strategy = "by_name"
```

---

## Options

| Option | Commands | Description | Default |
|---|---|---|---|
| `--strategy <name>` | delete, move, hardlink, tui | Which copy to keep: shortest, newest, oldest, or plugin name | shortest |
| `--dry-run` | delete, move, hardlink, tui | Preview without making any changes | ON |
| `--no-dry-run` | delete, move, hardlink, tui | Actually perform the action | — |
| `--interactive` | delete | Confirm each duplicate group before acting | OFF |
| `--older-than <days>` | delete | Only delete copies modified more than this many days ago | — |
| `--log <file>` | delete | Append a TSV log of every deleted file | — |
| `--plugin <file>` | delete, tui | Load a plugin .py file (repeatable) | — |
| `--config <file>` | all | Path to a config TOML file | ~/.dupegun.toml |
| `--min-size <size>` | all | Skip files smaller than this (e.g. 1MB) | 1 byte |
| `--max-size <size>` | all | Skip files larger than this (e.g. 100MB) | no limit |
| `--pattern <regex>` | all | Only scan filenames matching this regex | none |
| `--type <ext>` | all | Only include files with this extension (repeatable) | all types |
| `--exclude <name>` | all | Skip any folder with this name (repeatable) | none |
| `--summary` | scan | Print total wasted space only, no file list | OFF |
| `--count` | scan | Print group count and wasted space, then exit | OFF |
| `--json <file>` | scan | Export scan results to JSON | — |
| `--csv <file>` | scan | Export scan results to CSV | — |
| `--html <file>` | scan | Export a self-contained HTML report | — |

---

## How it works

dupegun uses a **3-pass engine** to detect duplicates accurately and efficiently:

```
Pass 1 — Group files by exact byte size
         (files with unique sizes are skipped immediately)

Pass 2 — Hash the first 4 KB of each size-match
         (quick pre-filter before full hashing)

Pass 3 — Full SHA-256 hash of remaining candidates
         (guaranteed accurate duplicate detection)
```

---

## Supported file types

dupegun works on **all file types** — it compares raw file contents, not names or extensions.

| Category | Examples |
|---|---|
| Documents | `.pdf` `.docx` `.xlsx` `.pptx` `.txt` |
| Images | `.jpg` `.png` `.gif` `.bmp` `.webp` |
| Videos | `.mp4` `.mkv` `.avi` `.mov` |
| Audio | `.mp3` `.wav` `.flac` `.aac` |
| Archives | `.zip` `.rar` `.7z` `.tar` `.gz` |
| Code | `.py` `.js` `.html` `.css` `.java` |
| Everything else | Any file, any extension |

---

## Safety

- **Dry-run is ON by default** on every destructive command. You always see a preview first.
- Use `--no-dry-run` only when you are sure.
- Use `--interactive` to confirm each group one by one.
- Use `move` instead of `delete` if you want a safety net.
- Use `--log` to keep a full audit trail of deletions.
- The TUI defaults to dry-run mode — use `--no-dry-run` to enable live deletion.

---

## Platform support

| Platform | Supported |
|---|---|
| Windows | Yes |
| Linux | Yes |
| macOS | Yes |

---

## Examples

```bash
# Interactive browse and delete
dupegun tui ~/Downloads --strategy newest

# Watch Downloads for duplicate photos in real time
dupegun watch ~/Downloads --type .jpg --type .png

# Set up your config once, never type flags again
dupegun config --init

# Full folder overview
dupegun stats ~/Downloads

# Generate an HTML report and open it in a browser
dupegun scan ~/Downloads --html report.html

# Delete duplicates with a plugin strategy and keep a log
dupegun delete ~/Downloads --plugin my_plugin.py --strategy by_name --no-dry-run --log deleted.log

# Find duplicate images, skip system folders
dupegun scan ~/Downloads --type .jpg --type .png --exclude cache --summary

# Compare active projects to a backup drive
dupegun compare ~/Projects /Volumes/BackupDrive/Projects
```

---

## Changelog

### v2.0.0
- **`tui` command**: Interactive terminal UI — browse duplicate groups, mark files, delete with keyboard shortcuts. Requires `pip install "dupegun[tui]"`.
- **`watch` command**: Monitor a folder in real time and alert when a duplicate appears. Requires `pip install "dupegun[watch]"`.
- **`config` command**: Create and manage `~/.dupegun.toml` to save your preferred defaults.
- **Plugin system**: Register custom keep-strategies with `@register_strategy("name")` and load plugins via `--plugin` or the config file.
- **`--config` flag** on all commands: use a custom config file.
- `tomli` added as a dependency for Python < 3.11 (TOML parsing).

### v1.3.0
- **`stats` command**: Show total files, total size, duplicate groups, duplicate files, and wasted space percentage.
- **`--html` flag on `scan`**: Generate a self-contained HTML report.
- **`--log` flag on `delete`**: Append a TSV audit log of every deleted file.

### v1.2.0
- **`compare` command**: Compare two directories to find cross-duplicates.
- **`--older-than` flag**: Auto-delete files based on age.
- **`--max-size` flag**: Combine with `--min-size` for size ranges.
- **`--pattern` flag**: Filter scans by regex filename patterns.
- Size parsing supports human-readable formats (e.g., `1MB`, `2GB`).

### v1.1.0
- **`--type` filter**: Scan only specific file extensions.
- **`--exclude` filter**: Skip folders by name.
- **`--summary` flag**: Show total wasted space without listing every file.
- **`--count` flag**: Print group count and wasted space in one line.

### v1.0.1
- Minor packaging fixes.

### v1.0.0
- Initial release: `scan`, `delete`, `move`, `hardlink` commands.
- 3-pass hashing engine.
- `--strategy`, `--dry-run`, `--interactive`, `--min-size`, `--json`, `--csv`.

---

## Contributing

Pull requests are welcome! To get started:

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
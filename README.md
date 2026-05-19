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
pip install dupegun
```

Requires Python 3.9 or higher.

---

## Quick Start

```bash
# Scan a folder and see all duplicates
dupegun scan ~/Downloads

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

# Combine filters — only duplicate JPEGs, skip cache folders
dupegun scan ~/Photos --type .jpg --exclude .thumbnails --summary
```

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

# Combine age filter with log
dupegun delete ~/Downloads --older-than 30 --no-dry-run --log deleted.log
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

Keeps the original copy in place. Moves all duplicates to the destination folder for you to review manually.

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

Replaces duplicate files with hard links. Both file paths remain on your system, but they share the same physical disk space — no data is lost.

---

## Options

| Option | Commands | Description | Default |
|---|---|---|---|
| `--strategy shortest` | delete, move, hardlink | Keep the file with the shortest path | Default |
| `--strategy newest` | delete, move, hardlink | Keep the most recently modified copy | — |
| `--strategy oldest` | delete, move, hardlink | Keep the oldest copy | — |
| `--dry-run` | delete, move, hardlink | Preview without making any changes | ON |
| `--no-dry-run` | delete, move, hardlink | Actually perform the action | — |
| `--interactive` | delete | Confirm each duplicate group before acting | OFF |
| `--older-than <days>` | delete | Only delete copies modified more than this many days ago | — |
| `--log <file>` | delete | Append a TSV log of every deleted file to this path | — |
| `--min-size <size>` | all | Skip files smaller than this size (e.g. 1MB) | 1 byte |
| `--max-size <size>` | all | Skip files larger than this size (e.g. 100MB) | no limit |
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

This approach is significantly faster than hashing every file — large folders with thousands of files are handled quickly.

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

Two files with different names but identical contents will always be detected.

---

## Safety

- **Dry-run is ON by default** on every destructive command (`delete`, `move`, `hardlink`). You always see a preview first.
- Use `--no-dry-run` only when you are sure.
- Use `--interactive` to confirm each group one by one.
- Use `move` instead of `delete` if you want a safety net.
- Use `--log` to keep a record of everything that was deleted.

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
# Find duplicate images in Downloads
dupegun scan ~/Downloads --type .jpg --type .png --type .gif

# Find duplicate videos, skip system folders
dupegun scan C:\ --type .mp4 --type .mkv --exclude Windows --exclude "Program Files"

# Quick summary — how much space am I wasting?
dupegun scan ~/Downloads --summary

# Just the count
dupegun scan ~/Downloads --count
# 47 duplicate group(s) found, 2.3 GB wasted

# Full folder overview
dupegun stats ~/Downloads

# Generate an HTML report and open it in a browser
dupegun scan ~/Downloads --html report.html

# Delete duplicates and keep a log of what was removed
dupegun delete ~/Downloads --strategy newest --no-dry-run --log deleted.log

# Find duplicates in Downloads, skip files under 500 KB
dupegun scan C:\Users\You\Downloads --min-size 500KB

# Delete duplicate images keeping the newest copy
dupegun delete ~/Photos --type .jpg --type .png --strategy newest --no-dry-run

# Move duplicates from two folders into one quarantine folder
dupegun move C:\Photos C:\Backup --dest C:\quarantine --no-dry-run

# Export full report to CSV and open in Excel
dupegun scan C:\Users\You\Documents --csv report.csv

# Compare active projects to a backup drive to find cross-duplicates
dupegun compare ~/Projects /Volumes/BackupDrive/Projects

# Find duplicates matching a specific filename pattern and size range
dupegun scan ~/Downloads --pattern "Copy of.*" --min-size 1MB --max-size 50MB
```

---

## Changelog

### v1.3.0
- **`stats` command**: Show total files, total size, duplicate groups, duplicate files, and wasted space percentage for any folder.
- **`--html` flag on `scan`**: Generate a self-contained HTML report with a dark theme — no external dependencies, just open in any browser.
- **`--log` flag on `delete`**: Append a TSV log of every deleted file (timestamp, action, kept path, deleted path, size). Appends across multiple runs so you have a full audit trail.

### v1.2.0
- **`compare` command**: Compare two directories to find cross-duplicates.
- **`--older-than` flag**: Auto-delete files based on age (safeguards recent files).
- **`--max-size` flag**: Combine with `--min-size` to scan specific size ranges.
- **`--pattern` flag**: Filter scans by regex filename patterns.
- Size parsing now supports human-readable formats (e.g., `1MB`, `2GB`).

### v1.1.0
- **`--type` filter**: Scan only specific file extensions (e.g. `--type .jpg --type .png`).
- **`--exclude` filter**: Skip folders by name (e.g. `--exclude node_modules`).
- **`--summary` flag**: Show total wasted space without printing every file.
- **`--count` flag**: Print duplicate group count and wasted space in one line.
- `--type` and `--exclude` available on all commands (`scan`, `delete`, `move`, `hardlink`).

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
pip install -e .
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
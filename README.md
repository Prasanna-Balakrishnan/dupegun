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
dupegun scan ~/Downloads --min-size 1000000

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

# Combine filters — only duplicate JPEGs, skip cache folders
dupegun scan ~/Photos --type .jpg --exclude .thumbnails --summary
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

# Delete only duplicate images, skip cache
dupegun delete ~/Photos --type .jpg --type .png --exclude .thumbnails --no-dry-run
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
| `--min-size <bytes>` | all | Skip files smaller than this size | 1 byte |
| `--type <ext>` | all | Only include files with this extension (repeatable) | all types |
| `--exclude <name>` | all | Skip any folder with this name (repeatable) | none |
| `--summary` | scan | Print total wasted space only, no file list | OFF |
| `--count` | scan | Print group count and wasted space, then exit | OFF |
| `--json <file>` | scan | Export scan results to JSON | — |
| `--csv <file>` | scan | Export scan results to CSV | — |

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

# Find duplicates in Downloads, skip files under 500 KB
dupegun scan C:\Users\You\Downloads --min-size 500000

# Delete duplicate images keeping the newest copy
dupegun delete ~/Photos --type .jpg --type .png --strategy newest --no-dry-run

# Move duplicates from two folders into one quarantine folder
dupegun move C:\Photos C:\Backup --dest C:\quarantine --no-dry-run

# Export full report to CSV and open in Excel
dupegun scan C:\Users\You\Documents --csv report.csv
```

---

## Changelog

### v1.1.0
- `--type` filter: scan only specific file extensions (e.g. `--type .jpg --type .png`)
- `--exclude` filter: skip folders by name (e.g. `--exclude node_modules`)
- `--summary` flag: show total wasted space without printing every file
- `--count` flag: print duplicate group count and wasted space in one line
- `--type` and `--exclude` are available on all commands (`scan`, `delete`, `move`, `hardlink`)

### v1.0.1
- Minor packaging fixes

### v1.0.0
- Initial release: `scan`, `delete`, `move`, `hardlink` commands
- 3-pass hashing engine
- `--strategy`, `--dry-run`, `--interactive`, `--min-size`, `--json`, `--csv`

---

## Contributing

Pull requests are welcome! To get started:

```bash
git clone https://github.com/YOUR_USERNAME/dupegun.git
cd dupegun
pip install -e .
pip install pytest
pytest tests/
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Author

Made by **Prasanna B**

If this tool helped you, consider giving it a star on GitHub!
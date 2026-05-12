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

# Export results to JSON
dupegun scan ~/Downloads --json results.json

# Export results to CSV
dupegun scan ~/Downloads --csv results.csv

# Export both at once
dupegun scan ~/Downloads --json results.json --csv results.csv
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

| Option | Description | Default |
|---|---|---|
| `--strategy shortest` | Keep the file with the shortest path | Default |
| `--strategy newest` | Keep the most recently modified copy | — |
| `--strategy oldest` | Keep the oldest copy | — |
| `--dry-run` | Preview without making any changes | ON |
| `--no-dry-run` | Actually perform the action | — |
| `--interactive` | Confirm each duplicate group before acting | OFF |
| `--min-size <bytes>` | Skip files smaller than this size | 1 byte |
| `--json <file>` | Export scan results to JSON | — |
| `--csv <file>` | Export scan results to CSV | — |

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
# Find duplicates in Downloads, skip files under 500 KB
dupegun scan C:\Users\You\Downloads --min-size 500000

# Delete duplicates keeping the newest copy
dupegun delete C:\Users\You\Downloads --strategy newest --no-dry-run

# Move duplicates from two folders into one quarantine folder
dupegun move C:\Photos C:\Backup --dest C:\quarantine --no-dry-run

# Export full report to CSV and open in Excel
dupegun scan C:\Users\You\Documents --csv report.csv
```

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

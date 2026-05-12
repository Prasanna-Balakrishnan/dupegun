# dupegun

Fast cross-platform duplicate file finder and cleaner for Windows, Linux and macOS.

## Install

```bash
pip install dupegun
```

## Commands

```bash
# Find duplicates
dupegun scan ~/Downloads

# Skip files under 1 MB
dupegun scan ~/Downloads --min-size 1000000

# Scan multiple folders
dupegun scan ~/Downloads ~/Documents ~/Desktop

# Export to JSON
dupegun scan ~/Downloads --json results.json

# Export to CSV
dupegun scan ~/Downloads --csv results.csv

# Preview what would be deleted (safe)
dupegun delete ~/Downloads --strategy newest

# Actually delete
dupegun delete ~/Downloads --strategy newest --no-dry-run

# Confirm each group before deleting
dupegun delete ~/Downloads --no-dry-run --interactive

# Move duplicates to quarantine
dupegun move ~/Downloads --dest ~/quarantine --no-dry-run

# Replace duplicates with hard links
dupegun hardlink ~/Downloads --no-dry-run
```

## Strategies

| Flag | Keeps |
|---|---|
| `--strategy shortest` | Shortest file path (default) |
| `--strategy newest` | Most recently modified copy |
| `--strategy oldest` | Oldest copy |

## Features

- Works on Windows, Linux, macOS
- All file types supported
- 3-pass engine (size → partial hash → full SHA-256)
- Colored terminal output
- Dry-run on by default (safe)
- JSON and CSV export
- Hard link support

## License

MIT
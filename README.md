# BibleDisk Caption Studio

BibleDisk Caption Studio is a desktop Bible verse caption app that reads scripture directly from SQLite and renders a subtitle-style preview inspired by your mockup.

## Features

- Read Bible content from `data/bible.db` inside the project folder
- Browse books, chapters, and verses from the SQLite database
- Preview Korean, English, and Spanish verse lines in a dark video-stage layout
- Attach a local video file and launch it in the system default player
- Export the selected verse as a three-line SubRip subtitle file (`.srt`)
- Copy the current verse block to the clipboard

## Requirements

- Python 3.10 or newer
- Windows 11 or macOS
- SQLite database file at `data/bible.db`, or set `BIBLEDISK_DB_PATH` to a custom location

The app uses only the Python standard library, including `sqlite3`, so no package install step is required.

## Run

```bash
python app.py
```

## Project Structure

- `app.py`: entry point
- `caption_app/ui.py`: Tkinter desktop UI with stage preview
- `caption_app/db.py`: SQLite repository for Bible data
- `caption_app/models.py`: caption and verse data structures
- `caption_app/srt.py`: SRT parsing and formatting
- `caption_app/storage.py`: legacy JSON persistence helpers
- `tests/test_srt.py`: parser/formatter tests
- `tests/test_db.py`: database integration checks

## Notes

- Video playback is handed off to the default media player on the machine. This keeps the app simple and Windows-friendly without extra dependencies.
- The UI is cross-platform. By default the app looks for the database at `data/bible.db` relative to the project root.
- If you store the database elsewhere, set `BIBLEDISK_DB_PATH` before launching the app.
# BibleCaptionApp

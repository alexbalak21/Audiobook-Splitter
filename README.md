# Audiobook Splitter

Split a chaptered `.m4b` audiobook into individual `.m4a` files, one per chapter, using ffmpeg's chapter metadata — with cover art extraction and both a GUI and a command-line mode.

## Features

- Reads chapter titles/timestamps directly from the `.m4b` file (no manual timing needed)
- Splits into one `.m4a` per chapter, using stream copy (no re-encoding, so it's fast and lossless)
- Extracts embedded cover art to `folder.jpg` / `folder.png` in the output folder
- Strips the source's full chapter table from each split file (so players don't show confusing extra chapters)
- Clean console output, with full debug detail written to `audiobook_splitter.log`
- Simple desktop GUI: pick a file, preview the chapter list, click Split

## Requirements

- Python 3.9+
- [ffmpeg](https://ffmpeg.org/download.html) installed and available at the path configured in `splitter.py` (`FFMPEG` constant, defaults to `C:\ffmpeg\bin\ffmpeg.exe`)
- Python packages listed in `requirements.txt`

Install dependencies:

```bash
pip install -r requirements.txt
```

The GUI uses Tkinter, which ships with most standard Python installations. If it's missing (some minimal Linux installs), install it via your system package manager (e.g. `sudo apt install python3-tk`).

## Configuration

Open `splitter.py` and set `FFMPEG` to the path of your `ffmpeg` executable:

```python
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"
```

On macOS/Linux this is typically just `"ffmpeg"` if it's on your `PATH`.

## Usage

### GUI (recommended)

```bash
python gui.py
```

1. Click **Select .m4b file...** and choose your audiobook.
2. The chapter list (title, start time, duration) is displayed automatically.
3. Click **Split**, then choose an output folder in the prompt.
4. Progress and status are shown live; a log panel shows what's happening.

Output files are named `01 - Chapter 1.m4a`, `02 - Chapter 2.m4a`, etc., and the cover art (if present) is saved alongside them as `folder.jpg`/`folder.png`.

### Command line

Edit `INPUT_FILE` at the top of `main.py` to point to your audiobook, then run:

```bash
python main.py
```

Chapters are split into an `output/` folder in the current directory. Progress is printed to the console; full debug detail is written to `audiobook_splitter.log`.

## Project structure

| File | Purpose |
|---|---|
| `gui.py` | Desktop GUI (Tkinter) — file picker, chapter preview, split button, progress/log |
| `main.py` | Command-line entry point |
| `chapters.py` | Reads chapter metadata and cover art from the `.m4b` via `mutagen` |
| `splitter.py` | Runs `ffmpeg` to extract each chapter as a separate `.m4a` |
| `requirements.txt` | Python dependencies |

## Troubleshooting

- **Nothing happens / hangs when splitting**: make sure the output folder is empty or that you're OK overwriting existing files — the tool passes `-y` to ffmpeg automatically, so this shouldn't normally block, but antivirus/file locks on Windows can still interfere.
- **"No embedded cover art found"**: not all `.m4b` files include cover art; this is just informational, not an error.
- **ffmpeg not found**: double-check the `FFMPEG` path in `splitter.py`, or make sure `ffmpeg` is on your system `PATH`.
- For anything else, check `audiobook_splitter.log` in the working directory — it contains full debug output, including raw chapter timestamps and ffmpeg's stderr on failure.

## How it works (technical notes)

- Chapter start/end times come from the `.m4b`'s own chapter list (read via `mutagen`); the end of each chapter is inferred as the start of the next one (or the file's total duration for the last chapter).
- Each chapter is extracted with `ffmpeg -ss <start> -i input.m4b -t <duration> -c copy ...` — seeking is done on the **input** side and duration (`-t`) is used instead of an absolute end time (`-to`), which avoids a common ffmpeg pitfall where `-to` gets interpreted relative to the original file instead of the seek point.
- `-map_chapters -1` strips the original chapter table from each output file so media players don't show leftover chapter markers from neighboring chapters.
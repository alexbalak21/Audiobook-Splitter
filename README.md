# Audiobook Splitter

Split a single `.m4b` audiobook file into one `.m4a` file per chapter, using its embedded chapter markers. Comes with both a command-line entry point and a desktop GUI.

## Features

- Reads chapter markers from `.m4b` files, including:
  - Standard Nero-style `chpl` chapter atoms (via `mutagen`)
  - QuickTime-style chapter tracks (via an automatic `ffprobe` fallback), which `mutagen` cannot parse on its own
- Splits the audiobook into per-chapter `.m4a` files using `ffmpeg` stream copy (fast, no re-encoding, no quality loss)
- Extracts embedded cover art (`folder.jpg` / `folder.png`) into the output folder
- Sanitizes chapter titles for use as filenames
- Full UTF-8 support for chapter titles (accents, non-Latin scripts, etc.)
- Desktop GUI (Tkinter) with a chapter preview table, progress bar, and live log console
- Detailed logging to both console/GUI and a rotating debug log file
- Standalone diagnostic script (`debug_chapters.py`) for inspecting a file's metadata when chapter detection fails

## Requirements

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/) (including `ffprobe`), installed and accessible on disk
- Python packages listed in `requirements.txt`:
  - `ffmpeg-python==0.2.0`
  - `future==1.0.0`
  - `mutagen==1.48.1`

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure FFmpeg path

Both `splitter.py` and `chapters.py` currently point to a hardcoded Windows path for `ffmpeg.exe` / `ffprobe.exe`:

```python
# splitter.py
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"

# chapters.py
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
```

Update these constants to match your local FFmpeg installation (or change them to just `"ffmpeg"` / `"ffprobe"` if both are already on your system `PATH`).

## Usage

### GUI

```bash
python gui.py
```

1. Click **Select .m4b file...** and choose your audiobook.
2. Review the detected chapters (title, start time, duration) in the table.
3. Click **Split**, then choose an output folder.
4. Progress and any warnings/errors appear in the log console at the bottom. A full debug log is also written to `audiobook_splitter.log`.

### Command line

Edit `INPUT_FILE` at the top of `main.py` to point to your `.m4b` file (default: `audiobook.m4b` in the current directory), then run:

```bash
python main.py
```

Output files are written to an `output/` folder by default, alongside `folder.jpg`/`folder.png` cover art if present.

### Debugging chapter detection issues

Some `.m4b` files (depending on which tool created them) store chapters in a format `mutagen` can't read directly — this shows up as `No chapters found in file.` even though the file clearly has chapters (e.g. visible in foobar2000). `chapters.py` already handles this automatically by falling back to `ffprobe`, but if you hit an issue that isn't covered by that fallback, run the standalone diagnostic script:

```bash
python debug_chapters.py "path/to/your/audiobook.m4b"
```

This dumps:
- Everything `mutagen` sees (tags, embedded chapters, file info)
- A manual scan of the raw MP4 atom structure, flagging whether the file uses a Nero `chpl` atom vs. a QuickTime-style chapter track
- The full `ffprobe -show_chapters` / `-show_streams` output as JSON

Share the output if you need help extending chapter support to a new format.

## Project structure

```
.
├── main.py              # CLI entry point
├── gui.py                # Tkinter GUI entry point
├── chapters.py            # Chapter reading (mutagen + ffprobe fallback) and cover art extraction
├── splitter.py            # ffmpeg-based audio splitting logic
├── debug_chapters.py       # Standalone chapter-detection diagnostic tool
├── requirements.txt
└── README.md
```

## How chapter detection works

1. `ChapterReader.load()` first asks `mutagen` for `MP4.chapters`.
2. If `mutagen` finds chapters, they're used directly.
3. If `mutagen` finds nothing, `ChapterReader` shells out to `ffprobe -show_chapters -print_format json` and parses the result instead. `ffprobe` output is decoded explicitly as UTF-8 (rather than relying on the system locale) so accented and non-ASCII chapter titles display correctly instead of showing up as mojibake (e.g. `CrÃ©dits` instead of `Crédits`).
4. If neither method finds chapters, a `ValueError` is raised and surfaced to the user (CLI: printed + logged; GUI: shown in an error dialog).

## Notes on splitting behavior

- `AudioSplitter.split()` uses `ffmpeg` stream copy (`-c copy`) — no re-encoding — so splitting is fast and lossless.
- The seek (`-ss`) is applied on ffmpeg's **input**, not the output, which avoids a common ffmpeg pitfall where an output-side `-to`/`-t` is interpreted against the original (pre-seek) timeline instead of relative to the seek point.
- Chapters with non-positive duration are skipped with a warning rather than causing a failure.
- The source file's full chapter table is stripped from each output file (`map_chapters=-1`) so each split file doesn't retain irrelevant chapter markers from the original.

## License

No license specified yet — add one here if you plan to share or publish this project.
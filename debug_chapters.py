# debug_chapters.py
"""
Diagnostic script to figure out why mutagen's MP4.chapters is empty
for some .m4b files that DO have chapters (e.g. visible in foobar2000).

Usage:
    python debug_chapters.py "C:/path/to/book.m4b"

What it does:
1. Dumps everything mutagen sees: mp4.chapters, raw tags, and any
   atom-like keys that might hint at a QuickTime text-track chapter
   list instead of the Nero-style 'chpl' atom mutagen expects.
2. Runs `ffprobe` (if available) and dumps its chapter list + full
   format/stream info as JSON, since ffprobe reads QuickTime text-track
   chapters that mutagen does not expose via .chapters.
3. Uses the raw mp4 box parser (via mutagen's atom access) to look for
   'chpl' (Nero chapters) vs a text/tx3g subtitle track (QuickTime
   chapters) so we know which format the file actually uses.
"""

import json
import subprocess
import sys
from pathlib import Path

FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"  # adjust if ffprobe lives elsewhere


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def dump_mutagen(path):
    section("MUTAGEN: MP4(...).chapters")
    try:
        from mutagen.mp4 import MP4
        mp4 = MP4(path)
    except Exception as e:
        print(f"Failed to open with mutagen: {e}")
        return None

    print(f"mp4.chapters = {mp4.chapters!r}")
    print(f"len(mp4.chapters) = {len(mp4.chapters) if mp4.chapters else 0}")

    section("MUTAGEN: mp4.info")
    print(f"length (s): {mp4.info.length}")
    print(f"bitrate: {getattr(mp4.info, 'bitrate', None)}")
    print(f"codec: {getattr(mp4.info, 'codec', None)}")

    section("MUTAGEN: mp4.tags (all keys)")
    if mp4.tags:
        for key in mp4.tags.keys():
            val = mp4.tags[key]
            # Truncate long/binary values for readability
            if isinstance(val, list) and val and hasattr(val[0], "__len__") and not isinstance(val[0], str):
                preview = f"<{len(val)} binary item(s)>"
            else:
                preview = repr(val)[:200]
            print(f"  {key!r}: {preview}")
    else:
        print("No tags found.")

    return mp4


def dump_raw_atoms(path):
    """Walk the raw MP4 box structure looking for chapter-related atoms:
    - 'chpl' = Nero-style chapter list (what mutagen's .chapters reads)
    - a 'trak' whose handler is 'text' or codec is 'tx3g'/'text' = QuickTime
      text-track chapters (common in Apple/iTunes-style .m4b files, and
      NOT parsed into mutagen's .chapters property)
    """
    section("RAW ATOM SCAN (looking for chpl vs text-track chapters)")
    try:
        from mutagen.mp4 import MP4
        mp4 = MP4(path)
        fileobj = open(path, "rb")
    except Exception as e:
        print(f"Could not open for raw scan: {e}")
        return

    try:
        atoms = mp4._MP4__atoms if hasattr(mp4, "_MP4__atoms") else None
    except Exception:
        atoms = None

    # mutagen doesn't expose a friendly public API for raw atom trees,
    # so fall back to a manual, minimal box walker.
    def read_boxes(f, end, depth=0):
        results = []
        while f.tell() < end:
            start = f.tell()
            header = f.read(8)
            if len(header) < 8:
                break
            size = int.from_bytes(header[0:4], "big")
            box_type = header[4:8].decode("latin1", errors="replace")
            if size == 1:
                largesize = int.from_bytes(f.read(8), "big")
                header_len = 16
                box_size = largesize
            elif size == 0:
                box_size = end - start
                header_len = 8
            else:
                box_size = size
                header_len = 8

            box_end = start + box_size
            results.append((depth, box_type, box_size, start))

            container_types = {"moov", "trak", "mdia", "minf", "stbl", "udta", "meta"}
            if box_type in container_types and box_size > header_len:
                f.seek(start + header_len)
                results.extend(read_boxes(f, box_end, depth + 1))

            f.seek(box_end)
        return results

    fileobj.seek(0, 2)
    file_end = fileobj.tell()
    fileobj.seek(0)
    boxes = read_boxes(fileobj, file_end)
    fileobj.close()

    found_chpl = False
    found_text_track = False

    for depth, box_type, size, start in boxes:
        indent = "  " * depth
        print(f"{indent}{box_type}  (size={size}, offset={start})")
        if box_type == "chpl":
            found_chpl = True
        if box_type == "text":
            found_text_track = True

    section("VERDICT (raw scan)")
    print(f"Found Nero-style 'chpl' atom (mutagen reads this): {found_chpl}")
    print(f"Found a 'text' sample-description box (hints at QuickTime")
    print(f"text-track chapters, which mutagen's .chapters does NOT read): {found_text_track}")
    if not found_chpl and found_text_track:
        print("\n=> This file almost certainly uses QuickTime-style text-track")
        print("   chapters. That's why mp4.chapters is empty even though")
        print("   foobar2000 (and ffprobe) can show chapters.")


def dump_ffprobe(path):
    section("FFPROBE: chapters + streams (JSON)")
    try:
        result = subprocess.run(
            [
                FFPROBE, "-v", "error",
                "-print_format", "json",
                "-show_chapters",
                "-show_streams",
                "-show_format",
                path,
            ],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        print(f"ffprobe not found at {FFPROBE!r}. Adjust the FFPROBE path")
        print("at the top of this script, or run ffprobe manually:")
        print(f'  ffprobe -v error -print_format json -show_chapters -show_streams "{path}"')
        return
    except Exception as e:
        print(f"ffprobe failed to run: {e}")
        return

    if result.returncode != 0:
        print("ffprobe exited with an error:")
        print(result.stderr.strip())
        return

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Could not parse ffprobe output as JSON. Raw output:")
        print(result.stdout)
        return

    chapters = data.get("chapters", [])
    print(f"ffprobe found {len(chapters)} chapter(s).")
    for c in chapters[:10]:
        title = c.get("tags", {}).get("title", "<untitled>")
        print(f"  id={c.get('id')} start={c.get('start_time')} end={c.get('end_time')} title={title!r}")
    if len(chapters) > 10:
        print(f"  ... and {len(chapters) - 10} more")

    section("FFPROBE: streams (to spot a subtitle/text chapter track)")
    for s in data.get("streams", []):
        print(
            f"  stream #{s.get('index')}: codec_type={s.get('codec_type')}, "
            f"codec_name={s.get('codec_name')}, tags={s.get('tags', {})}"
        )


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_chapters.py <path-to-m4b>")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"File not found: {path}")
        sys.exit(1)

    dump_mutagen(path)
    dump_raw_atoms(path)
    dump_ffprobe(path)


if __name__ == "__main__":
    main()
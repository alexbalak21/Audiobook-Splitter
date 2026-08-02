# chapters.py
import json
import logging
import subprocess

from mutagen.mp4 import MP4

logger = logging.getLogger(__name__)

# Some .m4b files store chapters as a Nero-style 'chpl' atom, which mutagen's
# MP4.chapters reads directly. Others (as produced by some audiobook tools)
# use a QuickTime-style chapter track instead -- a second video/text track
# linked to the main audio track via a 'tref' atom -- which mutagen does NOT
# parse into .chapters at all. ffprobe understands both, so we fall back to
# it whenever mutagen finds nothing.
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"


class Chapter:
    def __init__(self, index, title, start, end):
        self.index = index
        self.title = title
        self.start = start
        self.end = end

    def __repr__(self):
        return f"<Chapter {self.index}: {self.title} ({self.start} → {self.end})>"


class ChapterReader:
    def __init__(self, filename):
        self.filename = filename
        self.mp4 = MP4(filename)
        self.chapters = []

    def load(self):
        raw = self.mp4.chapters
        duration = self.mp4.info.length

        if raw:
            logger.debug("File duration: %.2fs, raw chapter count (mutagen): %d", duration, len(raw))
            for i, chap in enumerate(raw):
                title = chap.title if chap.title else f"Chapter {i+1}"
                start = chap.start
                end = raw[i + 1].start if i < len(raw) - 1 else duration
                self.chapters.append(Chapter(i + 1, title, start, end))
                logger.debug("Parsed chapter %d: '%s' start=%.2fs end=%.2fs", i + 1, title, start, end)
        else:
            logger.info(
                "mutagen found no chapters in '%s' (likely a QuickTime-style "
                "chapter track); falling back to ffprobe", self.filename
            )
            self.chapters = self._load_via_ffprobe(duration)

        if not self.chapters:
            raise ValueError("No chapters found in file.")

        logger.info("Loaded %d chapter(s) from '%s'", len(self.chapters), self.filename)
        return self.chapters

    def _load_via_ffprobe(self, duration):
        """Fallback chapter reader for files whose chapters mutagen can't see
        (e.g. QuickTime-style chapter tracks). Uses `ffprobe -show_chapters`,
        which parses both Nero 'chpl' atoms and QuickTime chapter tracks."""
        try:
            result = subprocess.run(
                [
                    FFPROBE, "-v", "error",
                    "-print_format", "json",
                    "-show_chapters",
                    self.filename,
                ],
                capture_output=True, timeout=60,
            )
            # ffprobe always writes UTF-8 JSON regardless of the system locale.
            # Decoding explicitly avoids mojibake (e.g. "Crédits" -> "CrÃ©dits")
            # that occurs if Python falls back to a locale encoding like cp1252.
            stdout_text = result.stdout.decode("utf-8", errors="replace")
            stderr_text = result.stderr.decode("utf-8", errors="replace")
        except FileNotFoundError:
            logger.error("ffprobe not found at '%s'; cannot use chapter fallback", FFPROBE)
            return []
        except Exception as e:
            logger.error("ffprobe failed to run: %s", e)
            return []

        if result.returncode != 0:
            logger.error("ffprobe exited with an error: %s", stderr_text.strip())
            return []

        try:
            data = json.loads(stdout_text)
        except json.JSONDecodeError:
            logger.error("Could not parse ffprobe output as JSON")
            return []

        raw_chapters = data.get("chapters", [])
        chapters = []
        for i, chap in enumerate(raw_chapters):
            title = chap.get("tags", {}).get("title") or f"Chapter {i + 1}"
            start = float(chap.get("start_time", 0))
            if i < len(raw_chapters) - 1:
                end = float(raw_chapters[i + 1].get("start_time", duration))
            else:
                end = float(chap.get("end_time", duration))
            chapters.append(Chapter(i + 1, title, start, end))
            logger.debug(
                "Parsed chapter %d via ffprobe: '%s' start=%.2fs end=%.2fs",
                i + 1, title, start, end,
            )

        return chapters

    def extract_cover(self, output_dir="output"):
        """Save the embedded cover art (if any) as output/folder.jpg or folder.png."""
        import os
        from mutagen.mp4 import MP4Cover

        covers = self.mp4.tags.get("covr") if self.mp4.tags else None
        if not covers:
            logger.info("No embedded cover art found in '%s'", self.filename)
            return None

        cover = covers[0]
        ext = "png" if cover.imageformat == MP4Cover.FORMAT_PNG else "jpg"
        out_path = os.path.join(output_dir, f"folder.{ext}")

        os.makedirs(output_dir, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(bytes(cover))

        logger.info("Saved cover art to '%s'", out_path)
        return out_path
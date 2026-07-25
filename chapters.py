# chapters.py
import logging

from mutagen.mp4 import MP4

logger = logging.getLogger(__name__)

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
        if not raw:
            raise ValueError("No chapters found in file.")

        duration = self.mp4.info.length
        logger.debug("File duration: %.2fs, raw chapter count: %d", duration, len(raw))

        # Compute end times
        for i, chap in enumerate(raw):
            title = chap.title if chap.title else f"Chapter {i+1}"
            start = chap.start

            if i < len(raw) - 1:
                end = raw[i + 1].start
            else:
                end = duration

            self.chapters.append(Chapter(i + 1, title, start, end))
            logger.debug("Parsed chapter %d: '%s' start=%.2fs end=%.2fs", i + 1, title, start, end)

        logger.info("Loaded %d chapter(s) from '%s'", len(self.chapters), self.filename)
        return self.chapters
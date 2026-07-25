# splitter.py
import logging
import os

import ffmpeg

logger = logging.getLogger(__name__)

FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"

INVALID_FILENAME_CHARS = '<>:"/\\|?*'


class AudioSplitter:
    def __init__(self, input_file, output_dir="output"):
        self.input_file = input_file
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def split(self, chapters, progress_callback=None):
        """
        progress_callback, if given, is called as progress_callback(i, total, chapter, status)
        after each chapter is processed. status is one of "ok", "skipped", "error".
        """
        total = len(chapters)
        logger.info("Splitting '%s' into %d chapter(s)", self.input_file, total)

        for i, chap in enumerate(chapters, start=1):
            title = self._safe_title(chap.title)
            output_file = os.path.join(self.output_dir, f"{chap.index:02d} - {title}.m4a")
            duration = chap.end - chap.start

            logger.info(
                "[%d/%d] %s  (start=%.2fs, duration=%.2fs) -> %s",
                i, total, chap.title, chap.start, duration, output_file,
            )

            if duration <= 0:
                logger.warning("Skipping '%s': non-positive duration (%.2fs)", chap.title, duration)
                if progress_callback:
                    progress_callback(i, total, chap, "skipped")
                continue

            try:
                (
                    ffmpeg
                    # IMPORTANT: -ss goes on the INPUT here, not the output.
                    # With stream copy this is still fast+accurate, and it avoids
                    # a well-known ffmpeg gotcha where an output-side -to is
                    # interpreted as an absolute timestamp on the ORIGINAL
                    # (pre-seek) timeline instead of being relative to -ss.
                    # That mismatch is what caused chapters to bleed into
                    # each other and end up with the wrong duration.
                    .input(self.input_file, ss=chap.start)
                    .output(
                        output_file,
                        t=duration,
                        c="copy",
                        map="0:a:0",
                        map_chapters=-1,  # strip the source's full chapter table
                        movflags="+faststart",
                    )
                    .global_args("-loglevel", "error", "-hide_banner", "-nostdin")
                    .run(cmd=FFMPEG, overwrite_output=True, quiet=True)
                )
            except ffmpeg.Error as e:
                stderr = e.stderr.decode(errors="ignore").strip() if e.stderr else str(e)
                last_line = stderr.splitlines()[-1] if stderr else "unknown error"
                logger.error("ffmpeg failed on '%s': %s", chap.title, last_line)
                logger.debug("Full ffmpeg stderr for '%s':\n%s", chap.title, stderr)
                if progress_callback:
                    progress_callback(i, total, chap, "error")
                raise

            logger.debug("Created: %s", output_file)
            if progress_callback:
                progress_callback(i, total, chap, "ok")

        logger.info("Done. %d file(s) written to '%s'", total, self.output_dir)

    @staticmethod
    def _safe_title(title):
        for ch in INVALID_FILENAME_CHARS:
            title = title.replace(ch, "_")
        return title.strip()
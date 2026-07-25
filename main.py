# main.py
import logging
import sys

from chapters import ChapterReader
from splitter import AudioSplitter

INPUT_FILE = "audiobook.m4b"
LOG_FILE = "audiobook_splitter.log"


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # capture everything; handlers filter what's shown

    # Console: short, readable, INFO and up only
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))

    # File: everything, with timestamps/module, for debugging
    file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    root.addHandler(console)
    root.addHandler(file_handler)


def main():
    setup_logging()
    logger = logging.getLogger("main")

    try:
        reader = ChapterReader(INPUT_FILE)
        chapters = reader.load()

        splitter = AudioSplitter(INPUT_FILE)
        splitter.split(chapters)
    except Exception:
        logger.exception("Splitting failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
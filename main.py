# main.py
from chapters import ChapterReader
from splitter import AudioSplitter

input_file = "audiobook.m4b"

reader = ChapterReader(input_file)
chapters = reader.load()

splitter = AudioSplitter(input_file)
splitter.split(chapters)

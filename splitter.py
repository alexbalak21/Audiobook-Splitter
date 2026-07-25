import ffmpeg
import os

FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"

class AudioSplitter:
    def __init__(self, input_file, output_dir="output"):
        self.input_file = input_file
        self.output_dir = output_dir

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def split(self, chapters):
        for chap in chapters:
            output_file = os.path.join(
                self.output_dir,
                f"{chap.index:02d} - {chap.title}.m4a"
            )

            (
                ffmpeg
                .input(self.input_file)
                .output(
                    output_file,
                    ss=chap.start,
                    to=chap.end,
                    c="copy",
                    map="0:a:0",
                    movflags="+faststart"
                )
                .run(cmd=FFMPEG)
            )

            print(f"Created: {output_file}")

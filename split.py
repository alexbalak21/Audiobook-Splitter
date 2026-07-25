from mutagen.mp4 import MP4
import ffmpeg
import os

input_file = "audiobook.m4b"
audio = MP4(input_file)

# Extract chapter list
chapters = audio.chapters
print(chapters)

for i, chap in enumerate(chapters):
    start = chap.start_time
    end = chap.end_time
    title = chap.subtitles[0] if chap.subtitles else f"Chapter_{i+1}"

    output_file = f"{i+1:02d}_{title}.m4a"

    (
        ffmpeg
        .input(input_file, ss=start, to=end)
        .output(output_file, c="copy")
        .run()
    )

    print(f"Created: {output_file}")

from mutagen.mp4 import MP4

def to_timestamp(seconds):
    # Convert seconds → mm:ss.ffffff
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:09.6f}"

file = "audiobook.m4b"
mp4 = MP4(file)

chapters = mp4.chapters
duration = mp4.info.length  # total duration in seconds

if not chapters:
    print("No chapters found.")
    exit()

# Compute end times
end_times = []
for idx, chap in enumerate(chapters):
    if idx < len(chapters) - 1:
        end_times.append(chapters[idx + 1].start)  # next chapter start
    else:
        end_times.append(duration)  # last chapter ends at file duration

# Display chapters
for i, chap in enumerate(chapters):
    title = chap.title if chap.title else f"Chapter {i+1}"
    start_seconds = chap.start
    end_seconds = end_times[i]

    print(f"=== Chapter {i+1} ===")
    print(f"Title: {title}")
    print(f"Start (sec):   {start_seconds:.6f}")
    print(f"Start (mm:ss): {to_timestamp(start_seconds)}")
    print(f"End   (mm:ss): {to_timestamp(end_seconds)}")
    print()

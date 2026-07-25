# gui.py
import logging
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from chapters import ChapterReader
from splitter import AudioSplitter

LOG_FILE = "audiobook_splitter.log"


class TextHandler(logging.Handler):
    """Logging handler that pushes formatted records into a thread-safe queue,
    so the Tk main loop (not the worker thread) can safely update the widget."""

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))


def setup_logging(log_queue):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    text_handler = TextHandler(log_queue)
    text_handler.setLevel(logging.INFO)
    text_handler.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    root.addHandler(text_handler)
    root.addHandler(file_handler)


def format_hms(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


class AudiobookSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audiobook Splitter")
        self.root.geometry("760x560")

        self.input_file = None
        self.chapters = []
        self.log_queue = queue.Queue()

        setup_logging(self.log_queue)
        self.logger = logging.getLogger("gui")

        self._build_widgets()
        self._poll_log_queue()

    # ---------- UI construction ----------

    def _build_widgets(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        self.file_label = ttk.Label(top, text="No file selected", foreground="#666")
        self.file_label.pack(side="left", padx=(0, 10))

        ttk.Button(top, text="Select .m4b file...", command=self.select_file).pack(side="right")

        # Chapters table
        table_frame = ttk.Frame(self.root, padding=(10, 0))
        table_frame.pack(fill="both", expand=True)

        columns = ("index", "title", "start", "duration")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        self.tree.heading("index", text="#")
        self.tree.heading("title", text="Title")
        self.tree.heading("start", text="Start")
        self.tree.heading("duration", text="Duration")
        self.tree.column("index", width=40, anchor="center")
        self.tree.column("title", width=380)
        self.tree.column("start", width=100, anchor="center")
        self.tree.column("duration", width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Split button + progress bar
        action_frame = ttk.Frame(self.root, padding=10)
        action_frame.pack(fill="x")

        self.split_button = ttk.Button(
            action_frame, text="Split", command=self.on_split_clicked, state="disabled"
        )
        self.split_button.pack(side="left")

        self.progress = ttk.Progressbar(action_frame, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=10)

        self.status_label = ttk.Label(action_frame, text="")
        self.status_label.pack(side="right")

        # Log console
        log_frame = ttk.LabelFrame(self.root, text="Log", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    # ---------- File selection / analysis ----------

    def select_file(self):
        path = filedialog.askopenfilename(
            title="Select an audiobook file",
            filetypes=[("Audiobook files", "*.m4b"), ("All files", "*.*")],
        )
        if not path:
            return

        self.input_file = path
        self.file_label.config(text=os.path.basename(path), foreground="black")
        self.split_button.config(state="disabled")
        self._clear_tree()

        try:
            reader = ChapterReader(path)
            self.chapters = reader.load()
        except Exception as e:
            self.logger.error("Failed to read chapters from '%s': %s", path, e)
            messagebox.showerror("Error", f"Could not read chapters from this file:\n{e}")
            self.chapters = []
            return

        for chap in self.chapters:
            duration = chap.end - chap.start
            self.tree.insert(
                "", "end",
                values=(chap.index, chap.title, format_hms(chap.start), format_hms(duration)),
            )

        self.split_button.config(state="normal")
        self.status_label.config(text=f"{len(self.chapters)} chapter(s) found")

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    # ---------- Splitting ----------

    def on_split_clicked(self):
        if not self.input_file or not self.chapters:
            return

        output_dir = filedialog.askdirectory(title="Select output folder")
        if not output_dir:
            return

        self.split_button.config(state="disabled")
        self.progress.config(maximum=len(self.chapters), value=0)
        self.status_label.config(text="Splitting...")

        thread = threading.Thread(
            target=self._run_split, args=(output_dir,), daemon=True
        )
        thread.start()

    def _run_split(self, output_dir):
        try:
            reader = ChapterReader(self.input_file)
            reader.extract_cover(output_dir)

            splitter = AudioSplitter(self.input_file, output_dir=output_dir)

            def progress_callback(i, total, chap, status):
                self.root.after(0, self._update_progress, i, total, chap, status)

            splitter.split(self.chapters, progress_callback=progress_callback)
            self.root.after(0, self._on_split_done, output_dir, None)
        except Exception as e:
            self.logger.exception("Splitting failed")
            self.root.after(0, self._on_split_done, output_dir, e)

    def _update_progress(self, i, total, chap, status):
        self.progress.config(value=i)
        self.status_label.config(text=f"[{i}/{total}] {chap.title} ({status})")

    def _on_split_done(self, output_dir, error):
        self.split_button.config(state="normal")
        if error:
            self.status_label.config(text="Failed")
            messagebox.showerror("Split failed", str(error))
        else:
            self.status_label.config(text="Done")
            messagebox.showinfo("Done", f"Chapters exported to:\n{output_dir}")

    # ---------- Log console updates ----------

    def _poll_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(150, self._poll_log_queue)


def main():
    root = tk.Tk()
    AudiobookSplitterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
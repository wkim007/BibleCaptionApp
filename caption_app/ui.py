from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from caption_app.db import BibleRepository, DB_PATH
from caption_app.models import CaptionEntry, VerseBundle
from caption_app.srt import format_srt


class CaptionStudioApp:
    def __init__(self) -> None:
        self.repository = BibleRepository()
        self.books = self.repository.list_books()
        self.current_bundle: VerseBundle | None = None

        self.root = tk.Tk()
        self.root.title("Bible DSK")
        self.root.geometry("1280x900")
        self.root.minsize(1080, 760)
        self.root.configure(bg="#111111")

        self.book_var = tk.StringVar()
        self.chapter_var = tk.StringVar()
        self.verse_var = tk.StringVar()
        self.duration_var = tk.StringVar(value="6.0")
        self.video_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value=f"Connected to {DB_PATH.name}")

        self.book_picker: tk.OptionMenu
        self.chapter_picker: tk.OptionMenu
        self.verse_picker: tk.OptionMenu
        self.preview_canvas: tk.Canvas
        self.reference_tag_id: int
        self.korean_text_id: int
        self.english_text_id: int
        self.spanish_text_id: int
        self.video_label_id: int

        self._build_menu()
        self._build_layout()
        self._load_initial_state()

    def run(self) -> None:
        self.root.mainloop()

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)

        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Choose Video...", command=self._choose_video)
        file_menu.add_command(label="Open Player", command=self._open_in_player)
        file_menu.add_separator()
        file_menu.add_command(label="Export Current Verse as SRT...", command=self._export_current_verse_srt)
        file_menu.add_command(label="Copy Current Verse", command=self._copy_current_verse)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)

        menu.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menu)

    def _build_layout(self) -> None:
        root = tk.Frame(self.root, bg="#111111")
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(0, weight=4)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        stage_frame = tk.Frame(root, bg="#111111", padx=18, pady=18)
        stage_frame.grid(row=0, column=0, sticky="nsew")
        stage_frame.grid_rowconfigure(0, weight=1)
        stage_frame.grid_columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            stage_frame,
            bg="#050505",
            highlightthickness=0,
            bd=0,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        self.preview_canvas.bind("<Configure>", self._redraw_preview)

        control_frame = tk.Frame(root, bg="#181818", padx=20, pady=20)
        control_frame.grid(row=0, column=1, sticky="nsew")
        control_frame.grid_columnconfigure(0, weight=1)

        self._make_title(control_frame, "Bible Caption Studio", 0)
        self._make_subtitle(control_frame, "Select a verse from SQLite and render it as a subtitle overlay.", 1)

        self._make_section_label(control_frame, "Video", 2)
        video_row = tk.Frame(control_frame, bg="#181818")
        video_row.grid(row=3, column=0, sticky="ew", pady=(8, 18))
        video_row.grid_columnconfigure(0, weight=1)

        tk.Entry(
            video_row,
            textvariable=self.video_path_var,
            bg="#242424",
            fg="#F3F3F3",
            insertbackground="#F3F3F3",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#343434",
            highlightcolor="#4E59FF",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=8)
        tk.Button(
            video_row,
            text="Browse",
            command=self._choose_video,
            bg="#F3F3F3",
            fg="#111111",
            relief="flat",
            activebackground="#FFFFFF",
            activeforeground="#111111",
            padx=14,
            pady=8,
        ).grid(row=0, column=1)

        self._make_section_label(control_frame, "Reference", 4)
        self.book_picker = self._make_option_menu(control_frame, 5, self.book_var, self._on_book_change)
        self.chapter_picker = self._make_option_menu(control_frame, 6, self.chapter_var, self._on_chapter_change)
        self.verse_picker = self._make_option_menu(control_frame, 7, self.verse_var, self._on_verse_change)

        self._make_section_label(control_frame, "Subtitle Duration (seconds)", 8)
        tk.Entry(
            control_frame,
            textvariable=self.duration_var,
            bg="#242424",
            fg="#F3F3F3",
            insertbackground="#F3F3F3",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#343434",
            highlightcolor="#4E59FF",
        ).grid(row=9, column=0, sticky="ew", ipady=8, pady=(8, 18))

        action_frame = tk.Frame(control_frame, bg="#181818")
        action_frame.grid(row=10, column=0, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)

        tk.Button(
            action_frame,
            text="Preview Verse",
            command=self._refresh_selected_verse,
            bg="#364BFF",
            fg="#F8F8F8",
            relief="flat",
            activebackground="#4358FF",
            activeforeground="#F8F8F8",
            padx=14,
            pady=12,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Button(
            action_frame,
            text="Export SRT",
            command=self._export_current_verse_srt,
            bg="#252525",
            fg="#F8F8F8",
            relief="flat",
            activebackground="#313131",
            activeforeground="#F8F8F8",
            padx=14,
            pady=12,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        tk.Button(
            control_frame,
            text="Copy Verse Text",
            command=self._copy_current_verse,
            bg="#252525",
            fg="#F8F8F8",
            relief="flat",
            activebackground="#313131",
            activeforeground="#F8F8F8",
            padx=14,
            pady=12,
        ).grid(row=11, column=0, sticky="ew", pady=(12, 8))

        tk.Button(
            control_frame,
            text="Open Video Player",
            command=self._open_in_player,
            bg="#252525",
            fg="#F8F8F8",
            relief="flat",
            activebackground="#313131",
            activeforeground="#F8F8F8",
            padx=14,
            pady=12,
        ).grid(row=12, column=0, sticky="ew")

        status = tk.Label(
            control_frame,
            textvariable=self.status_var,
            anchor="w",
            justify="left",
            wraplength=280,
            bg="#181818",
            fg="#B8B8B8",
            font=("Helvetica", 11),
        )
        status.grid(row=13, column=0, sticky="ew", pady=(22, 0))

    def _make_title(self, parent: tk.Widget, text: str, row: int) -> None:
        tk.Label(
            parent,
            text=text,
            bg="#181818",
            fg="#F4F4F4",
            anchor="w",
            font=("Helvetica", 22, "bold"),
        ).grid(row=row, column=0, sticky="ew")

    def _make_subtitle(self, parent: tk.Widget, text: str, row: int) -> None:
        tk.Label(
            parent,
            text=text,
            bg="#181818",
            fg="#B9B9B9",
            anchor="w",
            justify="left",
            wraplength=280,
            font=("Helvetica", 11),
        ).grid(row=row, column=0, sticky="ew", pady=(8, 24))

    def _make_section_label(self, parent: tk.Widget, text: str, row: int) -> None:
        tk.Label(
            parent,
            text=text,
            bg="#181818",
            fg="#7F7F7F",
            anchor="w",
            font=("Helvetica", 10, "bold"),
        ).grid(row=row, column=0, sticky="ew")

    def _make_option_menu(
        self,
        parent: tk.Widget,
        row: int,
        variable: tk.StringVar,
        command: callable,
    ) -> tk.OptionMenu:
        option = tk.OptionMenu(parent, variable, "")
        option.configure(
            bg="#242424",
            fg="#F3F3F3",
            activebackground="#313131",
            activeforeground="#F3F3F3",
            relief="flat",
            highlightthickness=0,
            direction="below",
            anchor="w",
        )
        option["menu"].configure(
            bg="#242424",
            fg="#F3F3F3",
            activebackground="#4E59FF",
            activeforeground="#F3F3F3",
        )
        option.grid(row=row, column=0, sticky="ew", pady=(8, 12))
        variable.trace_add("write", lambda *_: command())
        return option

    def _load_initial_state(self) -> None:
        if not self.books:
            raise RuntimeError("The SQLite database does not contain any Bible books.")
        self._set_menu_values(self.book_picker, self.book_var, [self._book_label(book) for book in self.books])

    def _on_book_change(self) -> None:
        book = self._selected_book()
        if book is None:
            return
        chapters = [str(chapter) for chapter in self.repository.list_chapters(book.book_id)]
        self._set_menu_values(self.chapter_picker, self.chapter_var, chapters)

    def _on_chapter_change(self) -> None:
        book = self._selected_book()
        chapter = self._selected_int(self.chapter_var)
        if book is None or chapter is None:
            return
        verses = [str(verse) for verse in self.repository.list_verses(book.book_id, chapter)]
        self._set_menu_values(self.verse_picker, self.verse_var, verses)

    def _on_verse_change(self) -> None:
        if self.verse_var.get().strip():
            self._refresh_selected_verse()

    def _refresh_selected_verse(self) -> None:
        book = self._selected_book()
        chapter = self._selected_int(self.chapter_var)
        verse = self._selected_int(self.verse_var)
        if book is None or chapter is None or verse is None:
            return

        try:
            self.current_bundle = self.repository.get_verse_bundle(book.book_id, chapter, verse)
        except Exception as error:
            messagebox.showerror("Verse lookup failed", str(error))
            return

        self._redraw_preview()
        self._set_status(f"Loaded {self.current_bundle.reference.label}")

    def _selected_book(self):
        value = self.book_var.get().strip()
        return next((book for book in self.books if self._book_label(book) == value), None)

    def _selected_int(self, variable: tk.StringVar) -> int | None:
        value = variable.get().strip()
        if not value:
            return None
        return int(value)

    def _book_label(self, book) -> str:
        return f"{book.book_id:02}  {book.korean_name} | {book.english_name}"

    def _set_menu_values(self, menu_widget: tk.OptionMenu, variable: tk.StringVar, values: list[str]) -> None:
        menu = menu_widget["menu"]
        menu.delete(0, "end")

        for value in values:
            menu.add_command(label=value, command=lambda item=value: variable.set(item))

        if values:
            variable.set(values[0])
        else:
            variable.set("")

    def _redraw_preview(self, _: object | None = None) -> None:
        canvas = self.preview_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 900)
        height = max(canvas.winfo_height(), 600)

        canvas.create_rectangle(0, 0, width, height, fill="#030303", outline="")
        canvas.create_text(
            28,
            28,
            anchor="nw",
            text="Bible DSK",
            fill="#A9A9A9",
            font=("Helvetica", 13, "bold"),
        )

        if self.video_path_var.get().strip():
            canvas.create_text(
                width - 26,
                28,
                anchor="ne",
                text=Path(self.video_path_var.get().strip()).name,
                fill="#7C7C7C",
                font=("Helvetica", 11),
            )

        overlay_height = min(220, int(height * 0.29))
        overlay_top = height - overlay_height
        self._draw_gradient(canvas, width, overlay_top, height)

        tag_text = "Select a verse"
        korean = "Choose a book, chapter, and verse from the SQLite Bible database."
        english = "The selected verse will appear here as a caption preview."
        spanish = "La vista previa de subtitulos mostrara el versiculo seleccionado."

        if self.current_bundle is not None:
            tag_text = self.current_bundle.reference.label
            korean = self.current_bundle.korean_text
            english = self.current_bundle.english_text
            spanish = self.current_bundle.spanish_text

        tag_width = min(max(280, len(tag_text) * 9), width - 80)
        canvas.create_rectangle(
            24,
            overlay_top - 38,
            24 + tag_width,
            overlay_top + 18,
            fill="#F4F4F1",
            outline="",
        )
        canvas.create_text(
            40,
            overlay_top - 10,
            anchor="w",
            text=tag_text,
            fill="#2F3FAD",
            font=("Helvetica", 15, "bold"),
        )

        text_left = 34
        text_width = width - 68
        canvas.create_text(
            text_left,
            overlay_top + 42,
            anchor="nw",
            width=text_width,
            text=korean,
            fill="#F3F3F3",
            font=("Helvetica", 18),
        )
        canvas.create_text(
            text_left,
            overlay_top + 92,
            anchor="nw",
            width=text_width,
            text=english,
            fill="#FFF36E",
            font=("Helvetica", 18),
        )
        canvas.create_text(
            text_left,
            overlay_top + 142,
            anchor="nw",
            width=text_width,
            text=spanish,
            fill="#FFC6A4",
            font=("Helvetica", 18),
        )

    def _draw_gradient(self, canvas: tk.Canvas, width: int, top: int, bottom: int) -> None:
        steps = max(bottom - top, 1)
        start = (41, 91, 255)
        end = (70, 42, 204)
        for offset in range(steps):
            mix = offset / steps
            red = int(start[0] + (end[0] - start[0]) * mix)
            green = int(start[1] + (end[1] - start[1]) * mix)
            blue = int(start[2] + (end[2] - start[2]) * mix)
            color = f"#{red:02x}{green:02x}{blue:02x}"
            y = top + offset
            canvas.create_line(0, y, width, y, fill=color)

    def _choose_video(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.wmv"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self.video_path_var.set(path)
        self._redraw_preview()
        self._set_status(f"Selected video: {Path(path).name}")

    def _open_in_player(self) -> None:
        path = self.video_path_var.get().strip()
        if not path:
            messagebox.showerror("No video selected", "Choose a video file first.")
            return
        if not Path(path).exists():
            messagebox.showerror("Missing file", "The selected video file does not exist.")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=True)
            else:
                subprocess.run(["xdg-open", path], check=True)
        except Exception as error:
            messagebox.showerror("Open failed", f"Could not open the video player.\n\n{error}")
            return

        self._set_status("Opened video in the default media player.")

    def _current_caption_entry(self) -> CaptionEntry:
        if self.current_bundle is None:
            raise ValueError("Select a verse before exporting subtitles.")

        try:
            duration_seconds = float(self.duration_var.get().strip())
        except ValueError as error:
            raise ValueError("Duration must be a number in seconds.") from error

        if duration_seconds <= 0:
            raise ValueError("Duration must be greater than zero.")

        text = "\n".join(
            [
                self.current_bundle.korean_text,
                self.current_bundle.english_text,
                self.current_bundle.spanish_text,
            ]
        ).strip()
        return CaptionEntry(
            start_ms=0,
            end_ms=int(duration_seconds * 1000),
            text=text,
        )

    def _export_current_verse_srt(self) -> None:
        try:
            entry = self._current_caption_entry()
        except ValueError as error:
            messagebox.showerror("Export failed", str(error))
            return

        suggested_name = "verse_caption.srt"
        if self.current_bundle is not None:
            ref = self.current_bundle.reference
            suggested_name = f"{ref.book_english}_{ref.chapter_num}_{ref.verse_num}.srt"

        path = filedialog.asksaveasfilename(
            title="Export subtitles",
            defaultextension=".srt",
            initialfile=suggested_name,
            filetypes=[("SubRip subtitles", "*.srt")],
        )
        if not path:
            return

        try:
            Path(path).write_text(format_srt([entry]), encoding="utf-8")
        except Exception as error:
            messagebox.showerror("Export failed", f"Could not export subtitles.\n\n{error}")
            return

        self._set_status(f"Exported subtitle: {Path(path).name}")

    def _copy_current_verse(self) -> None:
        if self.current_bundle is None:
            messagebox.showerror("Nothing to copy", "Select a verse first.")
            return

        payload = "\n".join(
            [
                self.current_bundle.reference.label,
                self.current_bundle.korean_text,
                self.current_bundle.english_text,
                self.current_bundle.spanish_text,
            ]
        )
        self.root.clipboard_clear()
        self.root.clipboard_append(payload)
        self._set_status("Copied current verse to clipboard.")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

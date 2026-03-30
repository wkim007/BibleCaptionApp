from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from caption_app.db import BibleRepository, DB_PATH
from caption_app.models import CaptionEntry, VerseBundle
from caption_app.srt import format_srt

FONT_CHOICES = sorted(
    [
        "Arial",
        "Helvetica",
        "Times New Roman",
        "Georgia",
        "Verdana",
        "Tahoma",
        "Trebuchet MS",
        "Garamond",
        "Palatino Linotype",
        "Book Antiqua",
        "Baskerville",
        "Cambria",
        "Calibri",
        "Candara",
        "Segoe UI",
        "Franklin Gothic Medium",
        "Gill Sans",
        "Futura",
        "Avenir Next",
        "Avenir",
        "Optima",
        "Didot",
        "Bodoni 72",
        "Rockwell",
        "Courier New",
        "Consolas",
        "Lucida Sans Unicode",
        "Century Gothic",
        "Corbel",
        "Constantia",
        "Monaco",
        "Menlo",
        "SF Pro Display",
        "SF Pro Text",
        "Roboto",
        "Open Sans",
        "Lato",
        "Montserrat",
        "Poppins",
        "Nunito",
        "Source Sans Pro",
        "Noto Sans",
        "Noto Serif",
        "PT Sans",
        "Ubuntu",
        "Malgun Gothic",
        "Apple SD Gothic Neo",
        "NanumGothic",
        "Noto Sans CJK KR",
        "Pretendard",
    ],
    key=str.casefold,
)


class CaptionStudioApp:
    def __init__(self) -> None:
        self.repository = BibleRepository()
        self.books = self.repository.list_books()
        self.current_bundle: VerseBundle | None = None
        self.panel_visible = True

        self.root = tk.Tk()
        self.root.title("Bible DSK")
        self.root.geometry("1280x900")
        self.root.minsize(1080, 760)
        self.root.configure(bg="#111111")

        self.book_var = tk.StringVar()
        self.chapter_var = tk.StringVar()
        self.verse_var = tk.StringVar()
        self.duration_var = tk.StringVar(value="6.0")
        self.text_font_var = tk.StringVar(value=self._default_preview_font())
        self.video_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value=f"Connected to {DB_PATH.name}")

        self.book_picker: tk.OptionMenu
        self.chapter_picker: tk.OptionMenu
        self.verse_picker: tk.OptionMenu
        self.font_combo: ttk.Combobox
        self.root_frame: tk.Frame
        self.stage_frame: tk.Frame
        self.control_frame: tk.Frame
        self.preview_canvas: tk.Canvas
        self.reference_tag_id: int
        self.korean_text_id: int
        self.english_text_id: int
        self.spanish_text_id: int
        self.video_label_id: int

        self._build_menu()
        self._build_layout()
        self._load_initial_state()
        self.root.bind_all("<Control-i>", self._toggle_panel_event)
        self.root.bind_all("<Control-I>", self._toggle_panel_event)

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
        self.root_frame = tk.Frame(self.root, bg="#111111")
        self.root_frame.pack(fill="both", expand=True)
        self.root_frame.grid_columnconfigure(0, weight=4)
        self.root_frame.grid_columnconfigure(1, weight=1)
        self.root_frame.grid_rowconfigure(0, weight=1)

        self.stage_frame = tk.Frame(self.root_frame, bg="#111111", padx=18, pady=18)
        self.stage_frame.grid(row=0, column=0, sticky="nsew")
        self.stage_frame.grid_rowconfigure(0, weight=1)
        self.stage_frame.grid_columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            self.stage_frame,
            bg="#050505",
            highlightthickness=0,
            bd=0,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        self.preview_canvas.bind("<Configure>", self._redraw_preview)

        self.control_frame = tk.Frame(self.root_frame, bg="#181818", padx=20, pady=20)
        self.control_frame.grid(row=0, column=1, sticky="nsew")
        self.control_frame.grid_columnconfigure(0, weight=1)
        self._configure_ttk_styles()

        header_frame = tk.Frame(self.control_frame, bg="#181818")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        self._make_title(header_frame, "Bible Caption Studio", 0)
        self._make_action_button(
            header_frame,
            text="x",
            command=self._hide_panel,
            bg="#2A2A2A",
            fg="#E6E6E6",
            hover_bg="#3A3A3A",
            font=("Helvetica", 13, "bold"),
            padx=12,
            pady=8,
        ).grid(row=0, column=1, sticky="ne")
        self._make_subtitle(self.control_frame, "Select a verse from SQLite and render it as a subtitle overlay.", 1)

        self._make_section_label(self.control_frame, "Video", 2)
        video_row = tk.Frame(self.control_frame, bg="#181818")
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
        self._make_action_button(
            video_row,
            text="Browse",
            command=self._choose_video,
            bg="#F3F3F3",
            fg="#111111",
            hover_bg="#FFFFFF",
            padx=18,
            pady=10,
        ).grid(row=0, column=1)

        self._make_section_label(self.control_frame, "Reference", 4)
        self.book_picker = self._make_option_menu(self.control_frame, 5, self.book_var, self._on_book_change)
        self.chapter_picker = self._make_option_menu(self.control_frame, 6, self.chapter_var, self._on_chapter_change)
        self.verse_picker = self._make_option_menu(self.control_frame, 7, self.verse_var, self._on_verse_change)

        self._make_section_label(self.control_frame, "Text Font", 8)
        self.font_combo = ttk.Combobox(
            self.control_frame,
            textvariable=self.text_font_var,
            values=FONT_CHOICES,
            state="readonly",
            style="BibleDisk.TCombobox",
        )
        self.font_combo.grid(row=9, column=0, sticky="ew", pady=(8, 18), ipady=6)
        self.font_combo.bind("<<ComboboxSelected>>", self._on_font_change)

        self._make_section_label(self.control_frame, "Subtitle Duration (seconds)", 10)
        tk.Entry(
            self.control_frame,
            textvariable=self.duration_var,
            bg="#242424",
            fg="#F3F3F3",
            insertbackground="#F3F3F3",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#343434",
            highlightcolor="#4E59FF",
        ).grid(row=11, column=0, sticky="ew", ipady=8, pady=(8, 18))

        action_frame = tk.Frame(self.control_frame, bg="#181818")
        action_frame.grid(row=12, column=0, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)

        self._make_action_button(
            action_frame,
            text="Preview Verse",
            command=self._refresh_selected_verse,
            bg="#364BFF",
            fg="#F8F8F8",
            hover_bg="#4358FF",
            padx=14,
            pady=12,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._make_action_button(
            action_frame,
            text="Export SRT",
            command=self._export_current_verse_srt,
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self._make_action_button(
            self.control_frame,
            text="Copy Verse Text",
            command=self._copy_current_verse,
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
        ).grid(row=13, column=0, sticky="ew", pady=(12, 8))

        self._make_action_button(
            self.control_frame,
            text="Open Video Player",
            command=self._open_in_player,
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
        ).grid(row=14, column=0, sticky="ew")

        status = tk.Label(
            self.control_frame,
            textvariable=self.status_var,
            anchor="w",
            justify="left",
            wraplength=280,
            bg="#181818",
            fg="#B8B8B8",
            font=("Helvetica", 11),
        )
        status.grid(row=15, column=0, sticky="ew", pady=(22, 0))

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

    def _make_action_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        bg: str,
        fg: str,
        hover_bg: str,
        padx: int = 14,
        pady: int = 12,
        font: tuple[str, int] | tuple[str, int, str] = ("Helvetica", 11, "bold"),
    ) -> tk.Label:
        button = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=font,
            padx=padx,
            pady=pady,
            cursor="hand2",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#343434",
            highlightcolor="#4E59FF",
        )
        button.bind("<Button-1>", lambda _: command())
        button.bind("<Enter>", lambda _: button.configure(bg=hover_bg))
        button.bind("<Leave>", lambda _: button.configure(bg=bg))
        return button

    def _configure_ttk_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "BibleDisk.TCombobox",
            fieldbackground="#242424",
            background="#242424",
            foreground="#F3F3F3",
            arrowcolor="#F3F3F3",
            bordercolor="#343434",
            lightcolor="#343434",
            darkcolor="#343434",
        )
        style.map(
            "BibleDisk.TCombobox",
            fieldbackground=[("readonly", "#242424")],
            background=[("readonly", "#242424")],
            foreground=[("readonly", "#F3F3F3")],
        )
        self.root.option_add("*TCombobox*Listbox.background", "#242424")
        self.root.option_add("*TCombobox*Listbox.foreground", "#F3F3F3")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#4E59FF")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#F3F3F3")

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
        self.font_combo.set(self.text_font_var.get())
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

    def _default_preview_font(self) -> str:
        if sys.platform == "darwin":
            return "Apple SD Gothic Neo"
        if sys.platform.startswith("win"):
            return "Malgun Gothic"
        return "Helvetica"

    def _preview_font_family(self) -> str:
        selected_font = self.text_font_var.get().strip()
        return selected_font or self._default_preview_font()

    def _on_font_change(self, _: object | None = None) -> None:
        self._redraw_preview()

    def _toggle_panel_event(self, _: object | None = None) -> None:
        self._set_panel_visible(not self.panel_visible)

    def _hide_panel(self) -> None:
        self._set_panel_visible(False)

    def _set_panel_visible(self, visible: bool) -> None:
        self.panel_visible = visible
        if visible:
            self.control_frame.grid()
            self.root_frame.grid_columnconfigure(1, weight=1)
            self.stage_frame.grid_configure(columnspan=1)
            self._set_status("Right panel shown. Press Ctrl+I to hide it.")
        else:
            self.control_frame.grid_remove()
            self.root_frame.grid_columnconfigure(1, weight=0)
            self.stage_frame.grid_configure(columnspan=2)
            self._set_status("Right panel hidden. Press Ctrl+I to show it again.")

    def _set_menu_values(self, menu_widget: tk.OptionMenu, variable: tk.StringVar, values: list[str]) -> None:
        menu = menu_widget["menu"]
        menu.delete(0, "end")

        for value in values:
            menu.add_command(label=value, command=lambda item=value: variable.set(item))

        if values:
            variable.set(values[0])
        else:
            variable.set("")

    def _measure_text_block(
        self,
        text: str,
        font_family: str,
        font_size: int,
        text_width: int,
        font_weight: str = "normal",
    ) -> tuple[tkfont.Font, int]:
        preview_font = tkfont.Font(family=font_family, size=font_size, weight=font_weight)
        line_spacing = preview_font.metrics("linespace")
        lines: list[str] = []

        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                lines.append("")
                continue

            current_line = words[0]
            for word in words[1:]:
                trial = f"{current_line} {word}"
                if preview_font.measure(trial) <= text_width:
                    current_line = trial
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)

        height = max(line_spacing * max(len(lines), 1), line_spacing)
        return preview_font, height

    def _resolve_overlay_layout(
        self,
        width: int,
        height: int,
        font_family: str,
        texts: tuple[str, str, str],
    ) -> dict[str, object]:
        text_width = width - 80
        minimum_overlay_top = int(height * 0.52)
        size_candidates: list[tuple[int, int, int]] = []

        for size_step in range(0, 11):
            korean_size = max(20, min(35, int(width * 0.028)) - size_step)
            english_size = max(19, min(33, int(width * 0.027)) - size_step)
            spanish_size = max(18, min(31, int(width * 0.026)) - size_step)
            size_candidates.append((korean_size, english_size, spanish_size))

        for korean_size, english_size, spanish_size in size_candidates:
            korean_font, korean_height = self._measure_text_block(texts[0], font_family, korean_size, text_width)
            english_font, english_height = self._measure_text_block(texts[1], font_family, english_size, text_width)
            spanish_font, spanish_height = self._measure_text_block(texts[2], font_family, spanish_size, text_width)

            top_padding = 28
            between_gap = 14
            bottom_padding = 18
            content_height = (
                top_padding
                + korean_height
                + between_gap
                + english_height
                + between_gap
                + spanish_height
                + bottom_padding
            )
            overlay_height = max(220, content_height)
            overlay_top = height - overlay_height

            if overlay_top >= minimum_overlay_top:
                return {
                    "overlay_top": overlay_top,
                    "overlay_height": overlay_height,
                    "text_width": text_width,
                    "korean_font": korean_font,
                    "english_font": english_font,
                    "spanish_font": spanish_font,
                    "korean_height": korean_height,
                    "english_height": english_height,
                    "spanish_height": spanish_height,
                    "top_padding": top_padding,
                    "between_gap": between_gap,
                }

        korean_font, korean_height = self._measure_text_block(texts[0], font_family, 20, text_width)
        english_font, english_height = self._measure_text_block(texts[1], font_family, 19, text_width)
        spanish_font, spanish_height = self._measure_text_block(texts[2], font_family, 18, text_width)
        overlay_top = minimum_overlay_top
        overlay_height = height - overlay_top
        return {
            "overlay_top": overlay_top,
            "overlay_height": overlay_height,
            "text_width": text_width,
            "korean_font": korean_font,
            "english_font": english_font,
            "spanish_font": spanish_font,
            "korean_height": korean_height,
            "english_height": english_height,
            "spanish_height": spanish_height,
            "top_padding": 24,
            "between_gap": 12,
        }

    def _redraw_preview(self, _: object | None = None) -> None:
        canvas = self.preview_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 900)
        height = max(canvas.winfo_height(), 600)
        font_family = self._preview_font_family()

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

        overlay_height = min(280, int(height * 0.34))
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

        layout = self._resolve_overlay_layout(width, height, font_family, (korean, english, spanish))
        overlay_top = int(layout["overlay_top"])
        self._draw_gradient(canvas, width, overlay_top, height)

        tag_width = min(max(360, len(tag_text) * 12), width - 80)
        canvas.create_rectangle(
            24,
            overlay_top - 58,
            24 + tag_width,
            overlay_top + 22,
            fill="#F4F4F1",
            outline="",
        )
        canvas.create_text(
            40,
            overlay_top - 18,
            anchor="w",
            text=tag_text,
            fill="#2F3FAD",
            font=(font_family, 23, "bold"),
        )

        text_left = 40
        text_width = int(layout["text_width"])
        current_y = overlay_top + int(layout["top_padding"])
        canvas.create_text(
            text_left,
            current_y,
            anchor="nw",
            width=text_width,
            text=korean,
            fill="#F3F3F3",
            font=layout["korean_font"],
        )
        current_y += int(layout["korean_height"]) + int(layout["between_gap"])
        canvas.create_text(
            text_left,
            current_y,
            anchor="nw",
            width=text_width,
            text=english,
            fill="#FFF36E",
            font=layout["english_font"],
        )
        current_y += int(layout["english_height"]) + int(layout["between_gap"])
        canvas.create_text(
            text_left,
            current_y,
            anchor="nw",
            width=text_width,
            text=spanish,
            fill="#FFC6A4",
            font=layout["spanish_font"],
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

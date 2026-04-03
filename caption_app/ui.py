from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
import tkinter.colorchooser as colorchooser
import tkinter.font as tkfont
import time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from caption_app.db import BibleRepository, DB_PATH
from caption_app.models import VerseBundle

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

FONT_SIZE_CHOICES = [str(size) for size in range(18, 49, 2)]


class CaptionStudioApp:
    NORMAL_STAGE_PADDING = 18

    def __init__(self) -> None:
        self.repository = BibleRepository()
        self.books = self.repository.list_books()
        self.current_bundle: VerseBundle | None = None
        self.imported_content: dict[str, str] | None = None
        self.panel_visible = True
        self.panel_width = 380
        self.playback_active = False
        self.subtitle_visible = True
        self.countdown_job: str | None = None
        self.countdown_end_time: float | None = None
        self.fullscreen_active = False

        self.root = tk.Tk()
        self.root.title("Bible Caption Studio")
        self.root.geometry("1280x900")
        self.root.minsize(1080, 760)
        self.root.configure(bg="#111111")
        self.menu_bar: tk.Menu | None = None

        self.book_var = tk.StringVar()
        self.chapter_var = tk.StringVar()
        self.verse_var = tk.StringVar()
        self.duration_var = tk.StringVar(value="6.0")
        self.text_font_var = tk.StringVar(value=self._default_preview_font())
        self.text_font_size_var = tk.StringVar(value="30")
        self.chapter_font_var = tk.StringVar(value=self._default_preview_font())
        self.chapter_font_size_var = tk.StringVar(value="23")
        self.preview_background_color_var = tk.StringVar(value="#000000")
        self.video_path_var = tk.StringVar()
        self.chapter_text_color_var = tk.StringVar(value="#2F3FAD")
        self.chapter_background_color_var = tk.StringVar(value="#F4F4F1")
        self.korean_text_color_var = tk.StringVar(value="#F3F3F3")
        self.english_text_color_var = tk.StringVar(value="#FFF36E")
        self.spanish_text_color_var = tk.StringVar(value="#FFC6A4")
        self.show_korean_var = tk.BooleanVar(value=True)
        self.show_english_var = tk.BooleanVar(value=True)
        self.show_spanish_var = tk.BooleanVar(value=True)
        self.countdown_var = tk.StringVar(value="6.0s")
        self.status_var = tk.StringVar(value=f"Connected to {DB_PATH.name}")

        self.book_picker: tk.OptionMenu
        self.chapter_picker: tk.OptionMenu
        self.verse_picker: tk.OptionMenu
        self.font_combo: ttk.Combobox
        self.font_size_combo: ttk.Combobox
        self.chapter_font_combo: ttk.Combobox
        self.chapter_font_size_combo: ttk.Combobox
        self.duration_spinbox: tk.Spinbox
        self.play_button: tk.Label
        self.default_settings_button: tk.Label
        self.root_frame: tk.Frame
        self.stage_frame: tk.Frame
        self.divider_frame: tk.Frame
        self.control_container: tk.Frame
        self.control_canvas: tk.Canvas
        self.control_scrollbar: tk.Scrollbar
        self.control_frame: tk.Frame
        self.control_window_id: int
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
        self.root.bind_all("<Control-f>", self._open_search_dialog)
        self.root.bind_all("<Control-F>", self._open_search_dialog)
        self.root.bind_all("<Control-s>", self._enter_fullscreen)
        self.root.bind_all("<Control-S>", self._enter_fullscreen)
        self.root.bind_all("<Escape>", self._exit_fullscreen)
        self.root.bind_all("<Left>", self._show_previous_verse)
        self.root.bind_all("<Right>", self._show_next_verse)
        self.root.bind_all("<Up>", self._show_next_book)
        self.root.bind_all("<Down>", self._show_previous_book)

    def run(self) -> None:
        self.root.mainloop()

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)

        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Choose Video...", command=self._choose_video)
        file_menu.add_command(label="Open Player", command=self._open_in_player)
        file_menu.add_separator()
        file_menu.add_command(label="Import TXT...", command=self._import_txt)
        file_menu.add_command(label="Export Current Verse as TXT...", command=self._export_current_verse_txt)
        file_menu.add_command(label="Copy Current Verse", command=self._copy_current_verse)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)

        menu.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menu)
        self.menu_bar = menu

    def _build_layout(self) -> None:
        self.root_frame = tk.Frame(self.root, bg="#111111")
        self.root_frame.pack(fill="both", expand=True)
        self.root_frame.grid_rowconfigure(0, weight=1)
        self.root_frame.grid_columnconfigure(0, weight=1)

        self.stage_frame = tk.Frame(
            self.root_frame,
            bg="#111111",
            padx=self.NORMAL_STAGE_PADDING,
            pady=self.NORMAL_STAGE_PADDING,
        )
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

        self.divider_frame = tk.Frame(self.root_frame, bg="#242424", width=8, cursor="sb_h_double_arrow")
        self.divider_frame.grid(row=0, column=1, sticky="ns")
        self.divider_frame.bind("<Button-1>", self._start_resize_panel)
        self.divider_frame.bind("<B1-Motion>", self._resize_panel_drag)

        self.root_frame.grid_columnconfigure(2, weight=0)

        self.control_container = tk.Frame(self.root_frame, bg="#181818", width=self.panel_width)
        self.control_container.grid(row=0, column=2, sticky="nsew")
        self.control_container.grid_propagate(False)

        self.control_canvas = tk.Canvas(
            self.control_container,
            bg="#181818",
            highlightthickness=0,
            bd=0,
            width=self.panel_width,
        )
        self.control_canvas.grid(row=0, column=0, sticky="nsew")

        self.control_scrollbar = tk.Scrollbar(
            self.control_container,
            orient="vertical",
            command=self.control_canvas.yview,
        )
        self.control_scrollbar.grid(row=0, column=1, sticky="ns")
        self.control_canvas.configure(yscrollcommand=self.control_scrollbar.set)

        self.control_container.grid_rowconfigure(0, weight=1)
        self.control_container.grid_columnconfigure(0, weight=1)

        self.control_frame = tk.Frame(self.control_canvas, bg="#181818", padx=20, pady=20)
        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_window_id = self.control_canvas.create_window((0, 0), window=self.control_frame, anchor="nw")
        self.control_frame.bind("<Configure>", self._sync_control_scrollregion)
        self.control_canvas.bind("<Configure>", self._resize_control_content)
        self.control_canvas.bind("<Enter>", self._bind_panel_mousewheel)
        self.control_canvas.bind("<Leave>", self._unbind_panel_mousewheel)
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
        tk.Label(
            self.control_frame,
            text="Ctrl + I will show/hide this panel",
            bg="#181818",
            fg="#D6D6D6",
            anchor="w",
            font=("Helvetica", 11, "bold"),
        ).grid(row=1, column=0, sticky="ew", pady=(6, 6))
        tk.Label(
            self.control_frame,
            text="Ctrl + s will full screen and Esc exits back to the normal windows",
            bg="#181818",
            fg="#D6D6D6",
            anchor="w",
            wraplength=320,
            justify="left",
            font=("Helvetica", 11, "bold"),
        ).grid(row=2, column=0, sticky="ew", pady=(0, 16))
        self._make_section_label(self.control_frame, "Bible Caption Studio Color", 3)
        self._make_action_button(
            self.control_frame,
            text="Pick Background Color",
            command=lambda: self._choose_text_color(
                self.preview_background_color_var,
                "Choose Bible Caption Studio background color",
            ),
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
        ).grid(row=4, column=0, sticky="ew", pady=(8, 18))

        self._make_section_label(self.control_frame, "Reference", 5)
        self.book_picker = self._make_option_menu(self.control_frame, 6, self.book_var, self._on_book_change)
        self.chapter_picker = self._make_option_menu(self.control_frame, 7, self.chapter_var, self._on_chapter_change)
        self.verse_picker = self._make_option_menu(self.control_frame, 8, self.verse_var, self._on_verse_change)

        self._make_section_label(self.control_frame, "Caption Chapter Style", 9)
        chapter_style_row = tk.Frame(self.control_frame, bg="#181818")
        chapter_style_row.grid(row=10, column=0, sticky="ew", pady=(8, 8))
        for column in range(2):
            chapter_style_row.grid_columnconfigure(column, weight=1)
        self.chapter_font_combo = ttk.Combobox(
            chapter_style_row,
            textvariable=self.chapter_font_var,
            values=FONT_CHOICES,
            state="readonly",
            style="BibleDisk.TCombobox",
        )
        self.chapter_font_combo.grid(row=0, column=0, sticky="ew", padx=(0, 6), ipady=6)
        self.chapter_font_combo.bind("<<ComboboxSelected>>", self._on_font_change)
        self.chapter_font_size_combo = ttk.Combobox(
            chapter_style_row,
            textvariable=self.chapter_font_size_var,
            values=FONT_SIZE_CHOICES,
            state="readonly",
            style="BibleDisk.TCombobox",
        )
        self.chapter_font_size_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0), ipady=6)
        self.chapter_font_size_combo.bind("<<ComboboxSelected>>", self._on_font_change)

        chapter_color_row = tk.Frame(self.control_frame, bg="#181818")
        chapter_color_row.grid(row=11, column=0, sticky="ew", pady=(0, 18))
        for column in range(2):
            chapter_color_row.grid_columnconfigure(column, weight=1)
        self._make_action_button(
            chapter_color_row,
            text="Text Color",
            command=lambda: self._choose_text_color(self.chapter_text_color_var, "Choose chapter text color"),
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=10,
            pady=10,
            font=("Helvetica", 10, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._make_action_button(
            chapter_color_row,
            text="Background",
            command=lambda: self._choose_text_color(self.chapter_background_color_var, "Choose chapter background color"),
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=10,
            pady=10,
            font=("Helvetica", 10, "bold"),
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self._make_section_label(self.control_frame, "Text Style", 12)
        text_style_row = tk.Frame(self.control_frame, bg="#181818")
        text_style_row.grid(row=13, column=0, sticky="ew", pady=(8, 18))
        for column in range(2):
            text_style_row.grid_columnconfigure(column, weight=1)

        self.font_combo = ttk.Combobox(
            text_style_row,
            textvariable=self.text_font_var,
            values=FONT_CHOICES,
            state="readonly",
            style="BibleDisk.TCombobox",
        )
        self.font_combo.grid(row=0, column=0, sticky="ew", padx=(0, 6), ipady=6)
        self.font_combo.bind("<<ComboboxSelected>>", self._on_font_change)

        self.font_size_combo = ttk.Combobox(
            text_style_row,
            textvariable=self.text_font_size_var,
            values=FONT_SIZE_CHOICES,
            state="readonly",
            style="BibleDisk.TCombobox",
        )
        self.font_size_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0), ipady=6)
        self.font_size_combo.bind("<<ComboboxSelected>>", self._on_font_change)

        self._make_section_label(self.control_frame, "Text Colors", 14)
        text_color_row = tk.Frame(self.control_frame, bg="#181818")
        text_color_row.grid(row=15, column=0, sticky="ew", pady=(8, 18))
        for column in range(3):
            text_color_row.grid_columnconfigure(column, weight=1)
        self._make_action_button(
            text_color_row,
            text="Korean Color",
            command=lambda: self._choose_text_color(self.korean_text_color_var, "Choose Korean text color"),
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
            font=("Helvetica", 10, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._make_action_button(
            text_color_row,
            text="English Color",
            command=lambda: self._choose_text_color(self.english_text_color_var, "Choose English text color"),
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
            font=("Helvetica", 10, "bold"),
        ).grid(row=0, column=1, sticky="ew", padx=6)
        self._make_action_button(
            text_color_row,
            text="Spanish Color",
            command=lambda: self._choose_text_color(self.spanish_text_color_var, "Choose Spanish text color"),
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
            font=("Helvetica", 10, "bold"),
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        self._make_section_label(self.control_frame, "Languages", 16)
        language_row = tk.Frame(self.control_frame, bg="#181818")
        language_row.grid(row=17, column=0, sticky="ew", pady=(8, 18))
        for column in range(3):
            language_row.grid_columnconfigure(column, weight=1)
        self._make_language_check(language_row, "Korean", self.show_korean_var).grid(row=0, column=0, sticky="w")
        self._make_language_check(language_row, "English", self.show_english_var).grid(row=0, column=1, sticky="w")
        self._make_language_check(language_row, "Spanish", self.show_spanish_var).grid(row=0, column=2, sticky="w")

        self._make_section_label(self.control_frame, "Caption Duration (seconds)", 18)
        duration_row = tk.Frame(self.control_frame, bg="#181818")
        duration_row.grid(row=19, column=0, sticky="ew", pady=(8, 8))
        duration_row.grid_columnconfigure(0, weight=1)
        duration_row.grid_columnconfigure(1, weight=0)
        self.duration_spinbox = tk.Spinbox(
            duration_row,
            from_=1.0,
            to=60.0,
            increment=0.5,
            format="%.1f",
            textvariable=self.duration_var,
            command=self._on_duration_change,
            bg="#242424",
            fg="#F3F3F3",
            buttonbackground="#2A2A2A",
            insertbackground="#F3F3F3",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#343434",
            highlightcolor="#4E59FF",
        )
        self.duration_spinbox.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=8)
        self.duration_spinbox.bind("<FocusOut>", self._on_duration_change)
        self.duration_spinbox.bind("<Return>", self._on_duration_change)
        self.play_button = self._make_action_button(
            duration_row,
            text="Play",
            command=self._toggle_duration_playback,
            bg="#364BFF",
            fg="#F8F8F8",
            hover_bg="#4358FF",
            padx=18,
            pady=10,
        )
        self.play_button.grid(row=0, column=1, sticky="ew")

        tk.Label(
            self.control_frame,
            textvariable=self.countdown_var,
            anchor="w",
            justify="left",
            bg="#181818",
            fg="#B8B8B8",
            font=("Helvetica", 11, "bold"),
        ).grid(row=20, column=0, sticky="ew", pady=(0, 18))

        action_frame = tk.Frame(self.control_frame, bg="#181818")
        action_frame.grid(row=21, column=0, sticky="ew")
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
            text="Export TXT",
            command=self._export_current_verse_txt,
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self._make_action_button(
            self.control_frame,
            text="Import TXT",
            command=self._import_txt,
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
        ).grid(row=22, column=0, sticky="ew", pady=(12, 8))
        self._make_action_button(
            self.control_frame,
            text="Copy Verse Text",
            command=self._copy_current_verse,
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
        ).grid(row=23, column=0, sticky="ew", pady=(0, 8))
        self.default_settings_button = self._make_action_button(
            self.control_frame,
            text="Default Settings",
            command=self._confirm_default_settings,
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=14,
            pady=12,
        )
        self.default_settings_button.grid(row=24, column=0, sticky="ew")

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
        status.grid(row=25, column=0, sticky="ew", pady=(22, 0))

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

    def _make_language_check(self, parent: tk.Widget, text: str, variable: tk.BooleanVar) -> tk.Checkbutton:
        checkbox = tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            command=self._redraw_preview,
            bg="#181818",
            fg="#F3F3F3",
            activebackground="#181818",
            activeforeground="#F3F3F3",
            selectcolor="#242424",
            highlightthickness=0,
            bd=0,
            relief="flat",
            anchor="w",
            font=("Helvetica", 10, "bold"),
        )
        return checkbox

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
        if sys.platform.startswith("win"):
            option_font = ("Malgun Gothic", 11)
            option.configure(font=option_font)
            option["menu"].configure(font=option_font)
        option.grid(row=row, column=0, sticky="ew", pady=(8, 12))
        variable.trace_add("write", lambda *_: command())
        return option

    def _load_initial_state(self) -> None:
        if not self.books:
            raise RuntimeError("The SQLite database does not contain any Bible books.")
        self._apply_default_settings_to_controls(redraw=False)
        self._on_duration_change()
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
        self._stop_duration_playback(show_subtitle=True, reset_countdown=True)
        self.imported_content = None
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

    def _find_book_by_name(self, raw_name: str):
        normalized = " ".join(raw_name.strip().split()).casefold()
        if not normalized:
            return None

        for book in self.books:
            candidates = {
                book.korean_name.casefold(),
                book.english_name.casefold(),
            }
            short_english = getattr(book, "english_name", "")
            if short_english:
                candidates.add(short_english.casefold())
            if normalized in candidates:
                return book
        return None

    def _selected_int(self, variable: tk.StringVar) -> int | None:
        value = variable.get().strip()
        if not value:
            return None
        return int(value)

    def _navigate_verse(self, direction: int) -> None:
        book = self._selected_book()
        chapter = self._selected_int(self.chapter_var)
        verse = self._selected_int(self.verse_var)
        if book is None or chapter is None or verse is None:
            return

        verses = self.repository.list_verses(book.book_id, chapter)
        if not verses:
            return

        try:
            current_index = verses.index(verse)
        except ValueError:
            current_index = 0

        target_index = current_index + direction
        if 0 <= target_index < len(verses):
            self.verse_var.set(str(verses[target_index]))
            return

        if direction > 0:
            chapters = self.repository.list_chapters(book.book_id)
            if chapter < chapters[-1]:
                next_chapter = chapter + 1
                next_verses = self.repository.list_verses(book.book_id, next_chapter)
                if next_verses:
                    self.chapter_var.set(str(next_chapter))
                    self.verse_var.set(str(next_verses[0]))
            return

        if chapter > 1:
            previous_chapter = chapter - 1
            previous_verses = self.repository.list_verses(book.book_id, previous_chapter)
            if previous_verses:
                self.chapter_var.set(str(previous_chapter))
                self.verse_var.set(str(previous_verses[-1]))

    def _show_previous_verse(self, event: object | None = None) -> None:
        self._navigate_verse(-1)

    def _show_next_verse(self, event: object | None = None) -> None:
        self._navigate_verse(1)

    def _navigate_book(self, direction: int) -> None:
        book = self._selected_book()
        chapter = self._selected_int(self.chapter_var)
        verse = self._selected_int(self.verse_var)
        if book is None or chapter is None or verse is None:
            return

        try:
            current_index = next(index for index, item in enumerate(self.books) if item.book_id == book.book_id)
        except StopIteration:
            return

        target_index = max(0, min(len(self.books) - 1, current_index + direction))
        target_book = self.books[target_index]
        if target_book.book_id == book.book_id:
            return

        target_chapter = min(chapter, target_book.chapter_count)
        target_verses = self.repository.list_verses(target_book.book_id, target_chapter)
        if not target_verses:
            return
        target_verse = min(verse, target_verses[-1])

        self.book_var.set(self._book_label(target_book))
        self.chapter_var.set(str(target_chapter))
        self.verse_var.set(str(target_verse))

    def _show_next_book(self, event: object | None = None) -> None:
        self._navigate_book(1)

    def _show_previous_book(self, event: object | None = None) -> None:
        self._navigate_book(-1)

    def _open_search_dialog(self, event: object | None = None) -> str | None:
        query = self._show_search_dialog()
        if query is None:
            return "break"
        self._search_and_navigate(query)
        return "break"

    def _show_search_dialog(self) -> str | None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Find Verse")
        dialog.transient(self.root)
        dialog.configure(bg="#181818")
        dialog.resizable(False, False)

        width = 680
        height = 300
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        position_x = root_x + max((root_width - width) // 2, 0)
        position_y = root_y + max((root_height - height) // 2, 0)
        dialog.geometry(f"{width}x{height}+{position_x}+{position_y}")

        result: dict[str, str | None] = {"value": None}
        search_var = tk.StringVar()

        container = tk.Frame(dialog, bg="#181818", padx=24, pady=24)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)

        tk.Label(
            container,
            text="Find Verse",
            bg="#181818",
            fg="#F4F4F4",
            anchor="w",
            font=("Helvetica", 20, "bold"),
        ).grid(row=0, column=0, sticky="ew")

        tk.Label(
            container,
            text="Enter a verse reference like 'John 1:1' or '요한복음 1:1'",
            bg="#181818",
            fg="#D6D6D6",
            anchor="w",
            justify="left",
            wraplength=620,
            font=("Helvetica", 15, "bold"),
        ).grid(row=1, column=0, sticky="ew", pady=(10, 16))

        entry = tk.Entry(
            container,
            textvariable=search_var,
            bg="#242424",
            fg="#F3F3F3",
            insertbackground="#F3F3F3",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#343434",
            highlightcolor="#4E59FF",
            font=("Helvetica", 18),
        )
        entry.grid(row=2, column=0, sticky="ew", ipady=10)

        button_row = tk.Frame(container, bg="#181818")
        button_row.grid(row=3, column=0, sticky="e", pady=(22, 0))
        button_row.grid_columnconfigure(0, minsize=130)
        button_row.grid_columnconfigure(1, minsize=150)

        def submit() -> None:
            result["value"] = search_var.get()
            dialog.destroy()

        def cancel() -> None:
            result["value"] = None
            dialog.destroy()

        self._make_action_button(
            button_row,
            text="OK",
            command=submit,
            bg="#364BFF",
            fg="#F8F8F8",
            hover_bg="#4358FF",
            padx=34,
            pady=14,
            font=("Helvetica", 13, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._make_action_button(
            button_row,
            text="Cancel",
            command=cancel,
            bg="#252525",
            fg="#F8F8F8",
            hover_bg="#313131",
            padx=34,
            pady=14,
            font=("Helvetica", 13, "bold"),
        ).grid(row=0, column=1, sticky="ew")

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.bind("<Return>", lambda _: submit())
        dialog.bind("<Escape>", lambda _: cancel())

        dialog.update_idletasks()
        dialog.grab_set()
        entry.focus_set()
        dialog.wait_window()
        value = result["value"]
        if value is None:
            return None
        return value.strip()

    def _search_and_navigate(self, query: str) -> None:
        raw = " ".join(query.strip().split())
        if not raw:
            messagebox.showerror("Search", "not found or invalid input")
            return

        try:
            book_name, reference = raw.rsplit(" ", 1)
            chapter_text, verse_text = reference.split(":", 1)
            chapter_num = int(chapter_text)
            verse_num = int(verse_text)
        except ValueError:
            messagebox.showerror("Search", "not found or invalid input")
            return

        if chapter_num <= 0 or verse_num <= 0:
            messagebox.showerror("Search", "not found or invalid input")
            return

        book = self._find_book_by_name(book_name)
        if book is None:
            messagebox.showerror("Search", "not found or invalid input")
            return

        if chapter_num > book.chapter_count:
            messagebox.showerror("Search", "not found or invalid input")
            return

        verses = self.repository.list_verses(book.book_id, chapter_num)
        if verse_num not in verses:
            messagebox.showerror("Search", "not found or invalid input")
            return

        self.book_var.set(self._book_label(book))
        self.chapter_var.set(str(chapter_num))
        self.verse_var.set(str(verse_num))

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

    def _selected_language_entries(self) -> list[tuple[str, str, str]]:
        if self.imported_content is not None:
            entries: list[tuple[str, str, str]] = []
            if self.show_korean_var.get():
                entries.append(("", self.imported_content["korean"], self.korean_text_color_var.get()))
            if self.show_english_var.get():
                entries.append(("", self.imported_content["english"], self.english_text_color_var.get()))
            if self.show_spanish_var.get():
                entries.append(("", self.imported_content["spanish"], self.spanish_text_color_var.get()))
            return entries
        if self.current_bundle is None:
            return []

        entries: list[tuple[str, str, str]] = []
        reference = self.current_bundle.reference
        if self.show_korean_var.get():
            entries.append((reference.book_korean, self.current_bundle.korean_text, self.korean_text_color_var.get()))
        if self.show_english_var.get():
            entries.append((reference.book_english, self.current_bundle.english_text, self.english_text_color_var.get()))
        if self.show_spanish_var.get():
            entries.append((reference.book_spanish, self.current_bundle.spanish_text, self.spanish_text_color_var.get()))
        return entries

    def _build_reference_label(self) -> str:
        if self.imported_content is not None:
            return self.imported_content["reference"]
        if self.current_bundle is None:
            return "Select a verse"

        reference = self.current_bundle.reference
        selected_books = [book_name for book_name, _, _ in self._selected_language_entries()]
        if not selected_books:
            return f"{reference.chapter_num}:{reference.verse_num}"
        return f"{' | '.join(selected_books)} {reference.chapter_num}:{reference.verse_num}"

    def _on_font_change(self, _: object | None = None) -> None:
        self._redraw_preview()

    def _choose_text_color(self, color_var: tk.StringVar, title: str) -> None:
        _, chosen = colorchooser.askcolor(color=color_var.get(), title=title)
        if not chosen:
            return
        color_var.set(chosen)
        self._redraw_preview()

    def _base_font_size(self) -> int:
        try:
            return max(18, min(48, int(self.text_font_size_var.get().strip())))
        except ValueError:
            return 30

    def _chapter_font_size(self) -> int:
        try:
            return max(14, min(48, int(self.chapter_font_size_var.get().strip())))
        except ValueError:
            return 23

    def _normalized_duration(self) -> float:
        try:
            duration = float(self.duration_var.get().strip())
        except ValueError:
            duration = 6.0
        duration = max(1.0, min(60.0, duration))
        return round(duration, 1)

    def _on_duration_change(self, _: object | None = None) -> None:
        duration = self._normalized_duration()
        self.duration_var.set(f"{duration:.1f}")
        if not self.playback_active:
            self.countdown_var.set(f"{duration:.1f}s")

    def _toggle_duration_playback(self) -> None:
        if self.playback_active:
            self._stop_duration_playback(show_subtitle=True, reset_countdown=True)
            self._set_status("Subtitle playback stopped.")
            return

        if self.current_bundle is None:
            messagebox.showerror("No verse selected", "Select a verse before starting subtitle playback.")
            return

        duration = self._normalized_duration()
        self.duration_var.set(f"{duration:.1f}")
        self.subtitle_visible = True
        self.playback_active = True
        self.countdown_end_time = time.monotonic() + duration
        self._update_play_button_text("Stop")
        self._tick_duration_playback()
        self._set_status("Subtitle playback started.")

    def _start_resize_panel(self, _: object | None = None) -> None:
        self.root.update_idletasks()

    def _resize_panel_drag(self, event: tk.Event) -> None:
        if not self.panel_visible:
            return
        total_width = self.root_frame.winfo_width()
        new_width = max(280, min(640, total_width - event.x_root + self.root_frame.winfo_rootx()))
        self.panel_width = new_width
        self.control_container.configure(width=self.panel_width)
        self.control_canvas.configure(width=self.panel_width)
        self._resize_control_content()

    def _apply_default_settings_to_controls(self, redraw: bool = True) -> None:
        default_font = self._default_preview_font()
        self.text_font_var.set(default_font)
        self.text_font_size_var.set("30")
        self.chapter_font_var.set(default_font)
        self.chapter_font_size_var.set("23")
        self.preview_background_color_var.set("#000000")
        self.chapter_text_color_var.set("#2F3FAD")
        self.chapter_background_color_var.set("#F4F4F1")
        self.korean_text_color_var.set("#F3F3F3")
        self.english_text_color_var.set("#FFF36E")
        self.spanish_text_color_var.set("#FFC6A4")
        self.show_korean_var.set(True)
        self.show_english_var.set(True)
        self.show_spanish_var.set(True)
        self.duration_var.set("6.0")
        self.countdown_var.set("6.0s")
        self.subtitle_visible = True
        self.imported_content = None
        self.chapter_font_combo.set(self.chapter_font_var.get())
        self.chapter_font_size_combo.set(self.chapter_font_size_var.get())
        self.font_combo.set(self.text_font_var.get())
        self.font_size_combo.set(self.text_font_size_var.get())
        if redraw:
            self._redraw_preview()

    def _confirm_default_settings(self) -> None:
        confirmed = messagebox.askokcancel(
            "Default Settings",
            "Reset all caption settings to their default values?",
        )
        if not confirmed:
            return
        self._stop_duration_playback(show_subtitle=True, reset_countdown=True)
        self._apply_default_settings_to_controls(redraw=True)
        self._set_status("Default settings restored.")

    def _tick_duration_playback(self) -> None:
        if not self.playback_active or self.countdown_end_time is None:
            return

        remaining = max(0.0, self.countdown_end_time - time.monotonic())
        self.countdown_var.set(f"{remaining:.1f}s")
        self.subtitle_visible = remaining > 0.0
        self._redraw_preview()

        if remaining <= 0.0:
            self.playback_active = False
            self.countdown_end_time = None
            self.countdown_job = None
            self._update_play_button_text("Play")
            self._set_status("Subtitle playback finished.")
            return

        self.countdown_job = self.root.after(100, self._tick_duration_playback)

    def _stop_duration_playback(self, show_subtitle: bool, reset_countdown: bool) -> None:
        if self.countdown_job is not None:
            self.root.after_cancel(self.countdown_job)
            self.countdown_job = None
        self.playback_active = False
        self.countdown_end_time = None
        self.subtitle_visible = show_subtitle
        self._update_play_button_text("Play")
        if reset_countdown:
            duration = self._normalized_duration()
            self.countdown_var.set(f"{duration:.1f}s")
        self._redraw_preview()

    def _update_play_button_text(self, text: str) -> None:
        self.play_button.configure(text=text)

    def _toggle_panel_event(self, _: object | None = None) -> None:
        self._set_panel_visible(not self.panel_visible)

    def _set_stage_padding(self, padding: int) -> None:
        self.stage_frame.configure(padx=padding, pady=padding)

    def _enter_fullscreen(self, _: object | None = None) -> str:
        self.fullscreen_active = True
        self._set_stage_padding(0)
        if sys.platform.startswith("win"):
            self.root.config(menu="")
        self.root.attributes("-fullscreen", True)
        return "break"

    def _exit_fullscreen(self, _: object | None = None) -> str | None:
        if not self.fullscreen_active:
            return None
        self.fullscreen_active = False
        self.root.attributes("-fullscreen", False)
        self._set_stage_padding(self.NORMAL_STAGE_PADDING)
        if sys.platform.startswith("win") and self.menu_bar is not None:
            self.root.config(menu=self.menu_bar)
        return "break"

    def _hide_panel(self) -> None:
        self._set_panel_visible(False)

    def _set_panel_visible(self, visible: bool) -> None:
        self.panel_visible = visible
        if visible:
            self.divider_frame.grid()
            self.control_container.grid()
            self.control_container.configure(width=self.panel_width)
            self.control_canvas.configure(width=self.panel_width)
            self._resize_control_content()
            self._set_status("Right panel shown. Press Ctrl+I to hide it.")
        else:
            self.divider_frame.grid_remove()
            self.control_container.grid_remove()
            self._set_status("Right panel hidden. Press Ctrl+I to show it again.")

    def _sync_control_scrollregion(self, _: object | None = None) -> None:
        self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))

    def _resize_control_content(self, event: tk.Event | None = None) -> None:
        canvas_width = event.width if event is not None else self.control_canvas.winfo_width()
        if canvas_width <= 1:
            return
        self.control_canvas.itemconfigure(self.control_window_id, width=canvas_width)
        self._sync_control_scrollregion()

    def _bind_panel_mousewheel(self, _: object | None = None) -> None:
        self.control_canvas.bind_all("<MouseWheel>", self._scroll_control_panel)
        self.control_canvas.bind_all("<Button-4>", self._scroll_control_panel)
        self.control_canvas.bind_all("<Button-5>", self._scroll_control_panel)

    def _unbind_panel_mousewheel(self, _: object | None = None) -> None:
        self.control_canvas.unbind_all("<MouseWheel>")
        self.control_canvas.unbind_all("<Button-4>")
        self.control_canvas.unbind_all("<Button-5>")

    def _scroll_control_panel(self, event: tk.Event) -> str | None:
        if not self.panel_visible:
            return None
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            raw_delta = getattr(event, "delta", 0)
            if raw_delta == 0:
                return None
            delta = -1 if raw_delta > 0 else 1
        self.control_canvas.yview_scroll(delta, "units")
        return "break"

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
        if not text.strip():
            return preview_font, 0
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

    def _draw_top_rounded_box(
        self,
        canvas: tk.Canvas,
        left: int,
        top: int,
        right: int,
        bottom: int,
        radius: int,
        fill: str,
    ) -> None:
        radius = max(0, min(radius, (right - left) // 2, (bottom - top)))
        if radius == 0:
            canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="")
            return

        canvas.create_rectangle(left, top + radius, right, bottom, fill=fill, outline="")
        canvas.create_rectangle(left + radius, top, right - radius, bottom, fill=fill, outline="")
        canvas.create_arc(
            left,
            top,
            left + radius * 2,
            top + radius * 2,
            start=90,
            extent=90,
            style="pieslice",
            outline="",
            fill=fill,
        )
        canvas.create_arc(
            right - radius * 2,
            top,
            right,
            top + radius * 2,
            start=0,
            extent=90,
            style="pieslice",
            outline="",
            fill=fill,
        )

    def _resolve_tag_layout(self, width: int, overlay_top: int, text: str) -> dict[str, object]:
        max_width = width - 28
        font_family = self.chapter_font_var.get().strip() or self._default_preview_font()
        font_size = self._chapter_font_size()
        horizontal_padding = 26
        vertical_padding = 14

        for size in range(font_size, 13, -1):
            tag_font = tkfont.Font(family=font_family, size=size, weight="bold")
            text_width = tag_font.measure(text)
            box_width = min(max_width, text_width + horizontal_padding * 2)
            if box_width <= max_width:
                line_height = tag_font.metrics("linespace")
                box_height = line_height + vertical_padding * 2
                text_y = overlay_top - box_height / 2
                return {
                    "font": tag_font,
                    "box_width": box_width,
                    "box_height": box_height,
                    "text_x": horizontal_padding,
                    "text_y": text_y,
                    "box_top": overlay_top - box_height,
                    "box_bottom": overlay_top,
                }

        fallback_font = tkfont.Font(family=font_family, size=14, weight="bold")
        line_height = fallback_font.metrics("linespace")
        box_height = line_height + vertical_padding * 2
        return {
            "font": fallback_font,
            "box_width": max_width,
            "box_height": box_height,
            "text_x": horizontal_padding,
            "text_y": overlay_top - box_height / 2,
            "box_top": overlay_top - box_height,
            "box_bottom": overlay_top,
        }
        canvas.create_arc(
            right - radius * 2,
            top,
            right,
            top + radius * 2,
            start=0,
            extent=90,
            style="pieslice",
            outline="",
            fill=fill,
        )

    def _resolve_overlay_layout(
        self,
        width: int,
        height: int,
        font_family: str,
        texts: tuple[str, str, str],
        base_font_size: int,
    ) -> dict[str, object]:
        text_width = width - 80
        minimum_overlay_top = int(height * 0.35)
        size_candidates: list[tuple[int, int, int]] = []

        for size_step in range(0, 11):
            korean_size = max(18, base_font_size - size_step)
            english_size = max(17, base_font_size - 1 - size_step)
            spanish_size = max(16, base_font_size - 2 - size_step)
            size_candidates.append((korean_size, english_size, spanish_size))

        for korean_size, english_size, spanish_size in size_candidates:
            korean_font, korean_height = self._measure_text_block(texts[0], font_family, korean_size, text_width)
            english_font, english_height = self._measure_text_block(texts[1], font_family, english_size, text_width)
            spanish_font, spanish_height = self._measure_text_block(texts[2], font_family, spanish_size, text_width)

            top_padding = 18
            between_gap = 8
            bottom_padding = 12
            active_heights = [value for value in (korean_height, english_height, spanish_height) if value > 0]
            if active_heights:
                content_height = top_padding + sum(active_heights) + between_gap * (len(active_heights) - 1) + bottom_padding
            else:
                content_height = top_padding + bottom_padding
            minimum_overlay_height = 52 + (18 * max(len(active_heights), 1))
            overlay_height = max(minimum_overlay_height, content_height)
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

        korean_font, korean_height = self._measure_text_block(texts[0], font_family, max(18, base_font_size - 4), text_width)
        english_font, english_height = self._measure_text_block(texts[1], font_family, max(17, base_font_size - 5), text_width)
        spanish_font, spanish_height = self._measure_text_block(texts[2], font_family, max(16, base_font_size - 6), text_width)
        top_padding = 18
        between_gap = 8
        bottom_padding = 12
        active_heights = [value for value in (korean_height, english_height, spanish_height) if value > 0]
        content_height = (
            top_padding + sum(active_heights) + between_gap * max(len(active_heights) - 1, 0) + bottom_padding
            if active_heights
            else top_padding + bottom_padding
        )
        overlay_height = min(height - 40, max(70, content_height))
        overlay_top = height - overlay_height
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

    def _redraw_preview(self, _: object | None = None) -> None:
        canvas = self.preview_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 900)
        height = max(canvas.winfo_height(), 600)
        font_family = self._preview_font_family()
        base_font_size = self._base_font_size()

        canvas.create_rectangle(0, 0, width, height, fill=self.preview_background_color_var.get(), outline="")

        if self.video_path_var.get().strip():
            canvas.create_text(
                width - 26,
                28,
                anchor="ne",
                text=Path(self.video_path_var.get().strip()).name,
                fill="#7C7C7C",
                font=("Helvetica", 11),
            )

        if not self.subtitle_visible:
            return

        tag_text = self._build_reference_label()
        selected_entries = self._selected_language_entries()
        if not selected_entries:
            if self.current_bundle is None:
                selected_entries = [
                    ("", "Choose a book, chapter, and verse from the SQLite Bible database.", "#F3F3F3"),
                    ("", "The selected verse will appear here as a caption preview.", "#FFF36E"),
                    ("", "La vista previa de subtitulos mostrara el versiculo seleccionado.", "#FFC6A4"),
                ]
            else:
                selected_entries = []

        layout_texts = tuple(text for _, text, _ in selected_entries)
        while len(layout_texts) < 3:
            layout_texts += ("",)
        layout = self._resolve_overlay_layout(width, height, font_family, layout_texts[:3], base_font_size)
        overlay_top = int(layout["overlay_top"])
        self._draw_gradient(canvas, width, overlay_top, height)

        tag_layout = self._resolve_tag_layout(width, overlay_top, tag_text)
        tag_width = int(tag_layout["box_width"])
        tag_left = 0
        tag_top = int(tag_layout["box_top"])
        tag_bottom = int(tag_layout["box_bottom"])
        self._draw_top_rounded_box(
            canvas,
            tag_left,
            tag_top,
            tag_left + tag_width,
            tag_bottom,
            radius=20,
            fill=self.chapter_background_color_var.get(),
        )
        canvas.create_text(
            int(tag_layout["text_x"]),
            int(tag_layout["text_y"]),
            anchor="w",
            text=tag_text,
            fill=self.chapter_text_color_var.get(),
            font=tag_layout["font"],
        )

        text_left = 40
        text_width = int(layout["text_width"])
        current_y = overlay_top + int(layout["top_padding"])
        font_keys = [
            ("korean_font", "korean_height"),
            ("english_font", "english_height"),
            ("spanish_font", "spanish_height"),
        ]
        for index, (_, text, color) in enumerate(selected_entries[:3]):
            font_key, height_key = font_keys[index]
            canvas.create_text(
                text_left,
                current_y,
                anchor="nw",
                width=text_width,
                text=text,
                fill=color,
                font=layout[font_key],
            )
            current_y += int(layout[height_key]) + int(layout["between_gap"])

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

    def _export_current_verse_txt(self) -> None:
        if self.current_bundle is None and self.imported_content is None:
            messagebox.showerror("Export failed", "Select a verse before exporting text.")
            return

        suggested_name = "verse_caption.txt"
        if self.current_bundle is not None and self.imported_content is None:
            ref = self.current_bundle.reference
            suggested_name = f"{ref.book_english}_{ref.chapter_num}_{ref.verse_num}.txt"

        path = filedialog.asksaveasfilename(
            title="Export text",
            defaultextension=".txt",
            initialfile=suggested_name,
            filetypes=[("Text files", "*.txt")],
        )
        if not path:
            return

        if self.imported_content is not None:
            reference_label = self.imported_content["reference"]
            korean_text = self.imported_content["korean"]
            english_text = self.imported_content["english"]
            spanish_text = self.imported_content["spanish"]
        else:
            reference_label = self.current_bundle.reference.label
            korean_text = self.current_bundle.korean_text
            english_text = self.current_bundle.english_text
            spanish_text = self.current_bundle.spanish_text

        payload = "\n".join(
            [
                reference_label,
                korean_text,
                english_text,
                spanish_text,
            ]
        )
        try:
            Path(path).write_text(payload, encoding="utf-8")
        except Exception as error:
            messagebox.showerror("Export failed", f"Could not export text.\n\n{error}")
            return

        self._set_status(f"Exported text: {Path(path).name}")

    def _copy_current_verse(self) -> None:
        if self.current_bundle is None and self.imported_content is None:
            messagebox.showerror("Nothing to copy", "Select a verse first.")
            return

        if self.imported_content is not None:
            reference_label = self.imported_content["reference"]
            korean_text = self.imported_content["korean"]
            english_text = self.imported_content["english"]
            spanish_text = self.imported_content["spanish"]
        else:
            reference_label = self.current_bundle.reference.label
            korean_text = self.current_bundle.korean_text
            english_text = self.current_bundle.english_text
            spanish_text = self.current_bundle.spanish_text

        payload = "\n".join(
            [
                reference_label,
                korean_text,
                english_text,
                spanish_text,
            ]
        )
        self.root.clipboard_clear()
        self.root.clipboard_append(payload)
        self._set_status("Copied current verse to clipboard.")

    def _import_txt(self) -> None:
        path = filedialog.askopenfilename(
            title="Import text",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            content = Path(path).read_text(encoding="utf-8").strip()
        except Exception as error:
            messagebox.showerror("Import failed", f"Could not open text file.\n\n{error}")
            return

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if len(lines) != 4:
            messagebox.showwarning("Invalid format", "invalid format")
            return

        reference, korean_text, english_text, spanish_text = lines
        if "|" not in reference or ":" not in reference:
            messagebox.showwarning("Invalid format", "invalid format")
            return

        self.imported_content = {
            "reference": reference,
            "korean": korean_text,
            "english": english_text,
            "spanish": spanish_text,
        }
        self._stop_duration_playback(show_subtitle=True, reset_countdown=True)
        self._redraw_preview()
        self._set_status(f"Imported text: {Path(path).name}")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

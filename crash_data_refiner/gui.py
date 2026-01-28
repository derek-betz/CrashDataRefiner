"""Desktop GUI for CrashDataRefiner."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional, Tuple
import webbrowser

try:
    from tkintermapview import TkinterMapView
except Exception:  # pragma: no cover - optional dependency for GUI previews
    TkinterMapView = None

from .geo import load_kmz_polygon, parse_coordinate
from .kmz_report import write_kmz_report
from .pdf_report import generate_pdf_report
from .refiner import CrashDataRefiner
from .refiner import _normalize_header
from .spreadsheets import read_spreadsheet, read_spreadsheet_headers, write_spreadsheet


@dataclass
class PipelineMessage:
    level: str
    message: str
    payload: Optional[Dict[str, Any]] = None


class GradientFrame(tk.Canvas):
    """Canvas that renders a soft gradient with a subtle glossy highlight."""

    def __init__(
        self,
        master: tk.Misc,
        colors: List[str],
        gloss_color: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)
        self._colors = colors
        self._gloss_color = gloss_color
        self.bind("<Configure>", self._draw_gradient)

    def _draw_gradient(self, _event: Optional[tk.Event] = None) -> None:
        self.delete("gradient")
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)

        if len(self._colors) < 2:
            color = self._colors[0] if self._colors else "#000000"
            self.create_rectangle(0, 0, width, height, fill=color, outline="", tags="gradient")
        else:
            segments = len(self._colors) - 1
            step_height = height / segments
            for index in range(segments):
                start_color = self._hex_to_rgb(self._colors[index])
                end_color = self._hex_to_rgb(self._colors[index + 1])
                start_y = int(index * step_height)
                end_y = int((index + 1) * step_height) if index + 1 < segments else height
                span = max(end_y - start_y, 1)
                for offset in range(span):
                    ratio = offset / span
                    color = self._interpolate(start_color, end_color, ratio)
                    y = start_y + offset
                    self.create_line(0, y, width, y, fill=color, tags="gradient")

        if self._gloss_color and height > 6:
            gloss_height = max(int(height * 0.35), 12)
            gloss_height = min(gloss_height, height)
            self.create_rectangle(
                0,
                0,
                width,
                gloss_height,
                fill=self._gloss_color,
                outline="",
                stipple="gray25",
                tags="gradient",
            )

        self.create_line(0, height - 1, width, height - 1, fill="#000000", tags="gradient")
        self.tag_lower("gradient")

    @staticmethod
    def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
        value = value.lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        value = value.ljust(6, "0")[:6]
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))

    @staticmethod
    def _interpolate(start: Tuple[int, int, int], end: Tuple[int, int, int], ratio: float) -> str:
        clamped = max(0.0, min(1.0, ratio))
        red = int(start[0] + (end[0] - start[0]) * clamped)
        green = int(start[1] + (end[1] - start[1]) * clamped)
        blue = int(start[2] + (end[2] - start[2]) * clamped)
        return f"#{red:02x}{green:02x}{blue:02x}"


class CrashRefinerApp:
    """Tk-based GUI for refining crash data with KMZ boundaries."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Crash Data Refiner")

        self._queue: queue.Queue[PipelineMessage] = queue.Queue()
        self._map_request_id = 0
        self._map_update_after_id: Optional[str] = None
        self._map_markers: List[Any] = []
        self._map_polygon: Optional[Any] = None
        self._map_supported = TkinterMapView is not None
        self._outputs_dir = Path(__file__).resolve().parents[1] / "outputs"
        self._last_pdf_path: Optional[Path] = None

        self._configure_theme()
        self._build_layout()
        self._ensure_window_size()
        self.root.after(200, self._poll_queue)

    def _ensure_window_size(self) -> None:
        self.root.update_idletasks()
        work_left, work_top, work_right, work_bottom = self._get_work_area()
        work_width = max(work_right - work_left, 1)
        work_height = max(work_bottom - work_top, 1)
        safety_margin = self._get_work_area_margin()
        safe_bottom = work_bottom - safety_margin

        req_width = max(self.root.winfo_reqwidth(), 1100)
        req_height = max(self.root.winfo_reqheight(), 820)

        target_width = min(req_width, int(work_width * 0.97))
        target_height = min(req_height, int(work_height * 0.97) - safety_margin)
        target_height = max(target_height, 480)

        x = work_left + max((work_width - target_width) // 2, 0)
        y = work_top + max((work_height - target_height) // 2, 0)
        self.root.geometry(f"{int(target_width)}x{int(target_height)}+{int(x)}+{int(y)}")

        self.root.update_idletasks()
        bottom = self.root.winfo_rooty() + self.root.winfo_height()
        if bottom > safe_bottom:
            overflow = bottom - safe_bottom
            target_height = max(int(target_height - overflow - safety_margin), 480)
            y = work_top + max((work_height - target_height) // 2, 0)
            self.root.geometry(f"{int(target_width)}x{int(target_height)}+{int(x)}+{int(y)}")

        min_width = min(int(target_width), int(work_width * 0.9))
        min_height = min(int(target_height), int(work_height * 0.85) - safety_margin)
        self.root.minsize(min_width, min_height)

    def _get_work_area(self) -> Tuple[int, int, int, int]:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                rect = wintypes.RECT()
                if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                    return rect.left, rect.top, rect.right, rect.bottom
            except Exception:
                pass
        return 0, 0, screen_width, screen_height

    def _get_work_area_margin(self) -> int:
        try:
            scaling = float(self.root.tk.call("tk", "scaling"))
        except tk.TclError:
            scaling = 1.0
        return max(int(18 * scaling), 12)

    def _configure_theme(self) -> None:
        try:
            self.root.tk.call("tk", "scaling", 1.2)
        except tk.TclError:
            pass

        palette = {
            "base": "#000000",
            "surface": "#050505",
            "surface_alt": "#0a0a0a",
            "card": "#0f0f0f",
            "overlay": "#0f0f0f",
            "field": "#050505",
            "field_hover": "#0f1d0f",
            "field_active": "#133113",
            "border": "#0f3b0f",
            "outline": "#0f3b0f",
            "accent": "#00ff41",
            "accent_active": "#00cc34",
            "accent_pressed": "#00b12d",
            "accent_dim": "#0a4f1c",
            "accent_soft": "#002b0f",
            "success": "#00ff41",
            "warning": "#96ff00",
            "error": "#ff3b3b",
            "text": "#00ff41",
            "muted": "#55b56f",
            "muted_alt": "#3c8a4d",
            "code_bg": "#010201",
            "hero_start": "#000000",
            "hero_end": "#000000",
            "hero_gloss": "#001503",
        }
        self._palette = palette

        self.root.configure(background=palette["base"])
        default_font = "{Courier New} 11"
        self.root.option_add("*Font", default_font)
        self.root.option_add("*TButton.Padding", 12)
        self.root.option_add("*TEntry*Font", default_font)
        self.root.option_add("*TCombobox*Listbox.font", default_font)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Background.TFrame", background=palette["base"])
        style.configure("Card.TFrame", background=palette["card"], borderwidth=1, relief=tk.FLAT)
        style.configure("CardBody.TFrame", background=palette["card"], borderwidth=1)
        style.configure("Glass.TFrame", background=palette["surface_alt"], relief=tk.FLAT, borderwidth=1)
        style.configure("Header.TFrame", background=palette["hero_start"])
        style.configure(
            "TLabel",
            background=palette["card"],
            foreground=palette["text"],
            font=("Courier New", 11),
        )
        style.configure(
            "Heading.TLabel",
            background=palette["card"],
            foreground=palette["text"],
            font=("Courier New", 22, "bold"),
        )
        style.configure(
            "Subheading.TLabel",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            font=("Courier New", 11),
        )
        style.configure(
            "Body.TLabel",
            background=palette["surface_alt"],
            foreground=palette["text"],
            font=("Courier New", 11),
        )
        style.configure(
            "SectionHeading.TLabel",
            background=palette["card"],
            foreground=palette["text"],
            font=("Courier New", 14, "bold"),
        )
        style.configure(
            "Hint.TLabel",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            font=("Courier New", 9),
            wraplength=320,
        )
        style.configure(
            "MetricValue.TLabel",
            background=palette["surface_alt"],
            foreground=palette["text"],
            font=("Courier New", 22, "bold"),
        )
        style.configure(
            "MetricCaption.TLabel",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            font=("Courier New", 10),
        )
        style.configure(
            "Primary.TButton",
            background=palette["accent_soft"],
            foreground=palette["text"],
            borderwidth=1,
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", palette["accent_active"]),
                ("pressed", palette["accent_pressed"]),
                ("disabled", palette["accent_dim"]),
            ],
            foreground=[("disabled", palette["muted_alt"])],
        )
        style.configure(
            "Secondary.TButton",
            background=palette["field"],
            foreground=palette["text"],
            borderwidth=1,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", palette["field_hover"]), ("pressed", palette["field_active"])],
            foreground=[("disabled", palette["muted_alt"])],
        )
        style.configure(
            "TEntry",
            fieldbackground=palette["field"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
            insertcolor=palette["text"],
            padding=8,
        )
        style.map(
            "TEntry",
            fieldbackground=[("active", palette["field_hover"]), ("focus", palette["field_active"])],
        )
        style.configure(
            "TCombobox",
            fieldbackground=palette["field"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["field"]), ("active", palette["field_hover"])],
        )
        style.configure("TScrollbar", background=palette["surface_alt"], troughcolor=palette["field"])
        style.configure(
            "TCheckbutton",
            background=palette["surface_alt"],
            foreground=palette["text"],
            indicatorcolor=palette["accent"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", palette["field_hover"])],
            foreground=[("disabled", palette["muted"])],
        )

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, style="Background.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        header = GradientFrame(
            container,
            colors=[self._palette["hero_start"], self._palette["hero_end"]],
            gloss_color=self._palette["hero_gloss"],
            height=110,
        )
        header.pack(fill=tk.X)
        header_title = tk.Label(
            header,
            text="Crash Data Refiner",
            bg=self._palette["hero_start"],
            fg=self._palette["text"],
            font=("Courier New", 24, "bold"),
        )
        header.create_window(32, 30, anchor="nw", window=header_title)
        header_subtitle = tk.Label(
            header,
            text="Filter Raw Crash Data and Generate KMZ, Map, and PDF Reports",
            bg=self._palette["hero_start"],
            fg=self._palette["muted"],
            font=("Courier New", 12),
        )
        header.create_window(34, 68, anchor="nw", window=header_subtitle)

        body = ttk.Frame(container, style="Background.TFrame", padding=(24, 18, 24, 24))
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        self._build_inputs_panel(body)
        self._build_status(body)

    def _build_inputs_panel(self, parent: ttk.Frame) -> None:
        outer = ttk.Frame(parent, style="Background.TFrame")
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(
            outer,
            background=self._palette["base"],
            highlightthickness=0,
            bd=0,
        )
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        inner = ttk.Frame(canvas, style="Background.TFrame")
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.columnconfigure(0, weight=1)

        def _sync_scroll_region(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_canvas_width(event: tk.Event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        def _on_mousewheel(event: tk.Event) -> None:
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(_event: tk.Event) -> None:
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(_event: tk.Event) -> None:
            canvas.unbind_all("<MouseWheel>")

        inner.bind("<Configure>", _sync_scroll_region)
        canvas.bind("<Configure>", _sync_canvas_width)
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        inner.bind("<Enter>", _bind_mousewheel)
        inner.bind("<Leave>", _unbind_mousewheel)

        self._build_inputs(inner)

    def _build_inputs(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(16, 12))
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Project Inputs", style="SectionHeading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        self.data_path_var = tk.StringVar()
        self.kmz_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.lat_column_var = tk.StringVar()
        self.lon_column_var = tk.StringVar()
        self.label_order_var = tk.StringVar(value="Left to right (west to east)")
        self.invalid_path_var = tk.StringVar()
        self.pdf_path_hint_var = tk.StringVar()
        self.pdf_data_path_var = tk.StringVar()
        self.pdf_data_hint_var = tk.StringVar()
        self.label_order_options = {
            "Left to right (west to east)": "west_to_east",
            "Bottom to top (south to north)": "south_to_north",
        }

        current_row = 1
        current_row = self._add_file_picker(
            card,
            label="Crash Data File",
            variable=self.data_path_var,
            row=current_row,
            filetypes=[("CSV or Excel", "*.csv *.xlsx *.xlsm")],
            command=self._on_select_data_file,
        )

        current_row = self._add_file_picker(
            card,
            label="Relevance Boundary (KMZ Polygon)",
            variable=self.kmz_path_var,
            row=current_row,
            filetypes=[("KMZ Files", "*.kmz")],
            command=self._on_select_kmz_file,
        )

        ttk.Label(
            card,
            text="Upload KMZ with only one polygon to set Relevance Boundary.",
            style="Hint.TLabel",
        ).grid(row=current_row, column=0, sticky="w", pady=(0, 8))
        current_row += 1

        ttk.Label(card, text="Latitude Column", style="Body.TLabel").grid(
            row=current_row, column=0, sticky="w"
        )
        current_row += 1
        self.lat_combo = ttk.Combobox(card, textvariable=self.lat_column_var, state="readonly")
        self.lat_combo.grid(row=current_row, column=0, sticky="ew", pady=(4, 8))
        self.lat_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._request_reference_map_update(),
        )
        current_row += 1

        ttk.Label(card, text="Longitude Column", style="Body.TLabel").grid(
            row=current_row, column=0, sticky="w"
        )
        current_row += 1
        self.lon_combo = ttk.Combobox(card, textvariable=self.lon_column_var, state="readonly")
        self.lon_combo.grid(row=current_row, column=0, sticky="ew", pady=(4, 8))
        self.lon_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._request_reference_map_update(),
        )
        current_row += 1

        ttk.Label(card, text="KMZ Label Order", style="Body.TLabel").grid(
            row=current_row, column=0, sticky="w"
        )
        current_row += 1
        self.label_order_combo = ttk.Combobox(
            card,
            textvariable=self.label_order_var,
            state="readonly",
            values=list(self.label_order_options.keys()),
        )
        self.label_order_combo.grid(row=current_row, column=0, sticky="ew", pady=(4, 8))
        current_row += 1

        current_row = self._add_file_picker(
            card,
            label="Refined Output File",
            variable=self.output_path_var,
            row=current_row,
            filetypes=[("CSV or Excel", "*.csv *.xlsx *.xlsm")],
            command=self._on_select_output_file,
            save_dialog=True,
        )

        ttk.Label(
            card,
            textvariable=self.invalid_path_var,
            style="Hint.TLabel",
        ).grid(row=current_row, column=0, sticky="w", pady=(0, 10))
        current_row += 1

        ttk.Label(card, text="Report Outputs", style="SectionHeading.TLabel").grid(
            row=current_row, column=0, sticky="w", pady=(12, 10)
        )
        current_row += 1

        output_frame = ttk.Frame(card, style="Glass.TFrame", padding=(12, 10))
        output_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 12))
        output_frame.columnconfigure(0, weight=1)

        ttk.Label(
            output_frame,
            text="Generate PDF Crash Report",
            style="Body.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            output_frame,
            text="One page per crash with aerial imagery and bulleted details.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        output_row = 2
        output_row = self._add_file_picker(
            output_frame,
            label="PDF Report Data File (optional)",
            variable=self.pdf_data_path_var,
            row=output_row,
            filetypes=[("CSV or Excel", "*.csv *.xlsx *.xlsm")],
            command=self._on_select_pdf_data_file,
        )
        ttk.Label(
            output_frame,
            text="Leave blank to use the refined output file.",
            style="Hint.TLabel",
        ).grid(row=output_row, column=0, sticky="w", pady=(0, 6))
        output_row += 1
        ttk.Label(
            output_frame,
            textvariable=self.pdf_path_hint_var,
            style="Hint.TLabel",
        ).grid(row=output_row, column=0, sticky="w")
        output_row += 1
        ttk.Label(
            output_frame,
            textvariable=self.pdf_data_hint_var,
            style="Hint.TLabel",
        ).grid(row=output_row, column=0, sticky="w", pady=(2, 0))
        output_row += 1
        current_row += 1

        self.generate_report_button = ttk.Button(
            output_frame,
            text="Generate PDF Crash Report",
            style="Secondary.TButton",
            command=self._on_generate_report,
        )
        self.generate_report_button.grid(row=output_row, column=0, sticky="ew", pady=(8, 0))
        output_row += 1
        self.report_progress = ttk.Progressbar(output_frame, mode="indeterminate")
        self.report_progress.grid(row=output_row, column=0, sticky="ew", pady=(6, 0))

        button_row = ttk.Frame(card, style="Card.TFrame")
        button_row.grid(row=current_row, column=0, sticky="ew")
        button_row.columnconfigure(0, weight=1)

        self.run_button = ttk.Button(
            button_row,
            text="Run Refinement",
            style="Primary.TButton",
            command=self._on_run,
        )
        self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        self.progress = ttk.Progressbar(button_row, mode="indeterminate")
        self.progress.grid(row=0, column=1, sticky="ew")
        current_row += 1

        ttk.Label(card, text="Run Summary", style="SectionHeading.TLabel").grid(
            row=current_row, column=0, sticky="w", pady=(16, 12)
        )
        current_row += 1

        summary = ttk.Frame(card, style="Glass.TFrame", padding=(16, 14))
        summary.grid(row=current_row, column=0, sticky="ew", pady=(0, 4))
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)
        summary.columnconfigure(2, weight=1)

        self.included_var = tk.StringVar(value="0")
        self.excluded_var = tk.StringVar(value="0")
        self.invalid_var = tk.StringVar(value="0")

        self._add_metric(summary, "Included", self.included_var, 0)
        self._add_metric(summary, "Excluded", self.excluded_var, 1)
        self._add_metric(summary, "Invalid Lat/Long", self.invalid_var, 2)

        self._update_invalid_path_label()

    def _build_status(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(20, 18))
        card.grid(row=0, column=1, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=3)
        card.rowconfigure(1, weight=2)

        self._build_reference_map(card, row=0)

        log_frame = ttk.Frame(card, style="Glass.TFrame", padding=(12, 12))
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_widget = tk.Text(
            log_frame,
            height=10,
            bg=self._palette["code_bg"],
            fg=self._palette["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self._palette["border"],
            wrap=tk.WORD,
            font=("Cascadia Code", 10),
        )
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        self.log_widget.configure(state=tk.DISABLED)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_widget.configure(yscrollcommand=scrollbar.set)

        action_row = ttk.Frame(card, style="Card.TFrame")
        action_row.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        action_row.columnconfigure(0, weight=1)

        self.open_folder_button = ttk.Button(
            action_row,
            text="Open Output Folder",
            style="Secondary.TButton",
            command=self._open_output_folder,
            state=tk.DISABLED,
        )
        self.open_folder_button.grid(row=0, column=0, sticky="ew")

        action_row.columnconfigure(1, weight=1)
        self.open_pdf_button = ttk.Button(
            action_row,
            text="Open PDF Report",
            style="Secondary.TButton",
            command=self._open_pdf_report,
            state=tk.DISABLED,
        )
        self.open_pdf_button.grid(row=0, column=1, sticky="ew", padx=(12, 0))

    def _add_metric(self, parent: ttk.Frame, label: str, variable: tk.StringVar, column: int) -> None:
        block = ttk.Frame(parent, style="Glass.TFrame")
        block.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        block.columnconfigure(0, weight=1)
        ttk.Label(block, textvariable=variable, style="MetricValue.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(block, text=label, style="MetricCaption.TLabel").grid(
            row=1, column=0, sticky="w"
        )

    def _build_reference_map(self, parent: ttk.Frame, *, row: int) -> None:
        map_frame = ttk.Frame(parent, style="Glass.TFrame", padding=(12, 12))
        map_frame.grid(row=row, column=0, sticky="nsew", pady=(0, 16))
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(2, weight=1)

        ttk.Label(map_frame, text="Reference Map", style="Body.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        self.map_status_var = tk.StringVar(
            value="Load crash data and KMZ boundary to preview."
        )
        ttk.Label(map_frame, textvariable=self.map_status_var, style="Hint.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 8)
        )

        if self._map_supported and TkinterMapView:
            self.map_widget = TkinterMapView(map_frame, corner_radius=8, height=320)
            self.map_widget.grid(row=2, column=0, sticky="nsew")
            self.map_widget.set_position(39.5, -98.35)
            self.map_widget.set_zoom(4)
        else:
            self.map_widget = None
            ttk.Label(
                map_frame,
                text="Install tkintermapview to enable the reference map preview.",
                style="Hint.TLabel",
            ).grid(row=2, column=0, sticky="w")

    def _add_file_picker(
        self,
        parent: ttk.Frame,
        *,
        label: str,
        variable: tk.StringVar,
        row: int,
        filetypes: List[Tuple[str, str]],
        command: Optional[callable] = None,
        save_dialog: bool = False,
    ) -> int:
        ttk.Label(parent, text=label, style="Body.TLabel").grid(row=row, column=0, sticky="w")
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=row + 1, column=0, sticky="ew", pady=(4, 8))
        frame.columnconfigure(0, weight=1)
        entry = ttk.Entry(frame, textvariable=variable)
        entry.grid(row=0, column=0, sticky="ew")
        button = ttk.Button(
            frame,
            text="Browse",
            style="Secondary.TButton",
            command=lambda: self._browse_file(variable, filetypes, command, save_dialog),
        )
        button.grid(row=0, column=1, padx=(8, 0))
        return row + 2

    def _browse_file(
        self,
        variable: tk.StringVar,
        filetypes: List[Tuple[str, str]],
        command: Optional[callable],
        save_dialog: bool,
    ) -> None:
        if save_dialog:
            path = filedialog.asksaveasfilename(
                filetypes=filetypes,
                initialdir=str(self._ensure_outputs_dir()),
            )
        else:
            path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            variable.set(path)
            if command:
                command()

    def _on_select_data_file(self) -> None:
        path = self.data_path_var.get().strip()
        if not path:
            return
        try:
            headers = read_spreadsheet_headers(path)
        except Exception as exc:
            messagebox.showerror("Crash Data Refiner", f"Failed to read headers: {exc}")
            return
        self._update_column_choices(headers)
        self._suggest_output_path(path)

    def _on_select_kmz_file(self) -> None:
        self._request_reference_map_update()

    def _on_select_output_file(self) -> None:
        output_path = self.output_path_var.get().strip()
        if output_path:
            resolved = self._resolve_output_path(output_path)
            if str(resolved) != output_path:
                self.output_path_var.set(str(resolved))
        self._update_invalid_path_label()

    def _on_select_pdf_data_file(self) -> None:
        pdf_path = self.pdf_data_path_var.get().strip()
        if pdf_path:
            resolved = Path(pdf_path)
            if resolved.exists() and resolved.is_file():
                self.pdf_data_path_var.set(str(resolved))
                try:
                    headers = read_spreadsheet_headers(str(resolved))
                except Exception as exc:
                    messagebox.showerror("Crash Data Refiner", f"Failed to read headers: {exc}")
                else:
                    self._update_column_choices(headers, prefer_existing=True)
        self._update_invalid_path_label()

    def _update_invalid_path_label(self) -> None:
        output_path = self.output_path_var.get().strip()
        outputs_dir = self._ensure_outputs_dir()
        if not output_path:
            self.invalid_path_var.set(f"Outputs will be saved to {outputs_dir}.")
            resolved: Optional[Path] = None
        else:
            resolved = self._resolve_output_path(output_path)
            self.invalid_path_var.set(f"Outputs will be saved to {outputs_dir}.")

        pdf_data_path = self.pdf_data_path_var.get().strip()
        if resolved is not None:
            pdf_path = self._pdf_output_path(resolved)
            self.pdf_path_hint_var.set(f"PDF report: {pdf_path.name}")
        else:
            self.pdf_path_hint_var.set("PDF report will be saved to the outputs folder.")
        if pdf_data_path:
            self.pdf_data_hint_var.set(f"PDF data source: {Path(pdf_data_path).name}")
        else:
            self.pdf_data_hint_var.set("PDF data source: refined output file")

    def _ensure_outputs_dir(self) -> Path:
        self._outputs_dir.mkdir(parents=True, exist_ok=True)
        return self._outputs_dir

    def _resolve_output_path(self, output_path: str) -> Path:
        outputs_dir = self._ensure_outputs_dir()
        if output_path:
            filename = Path(output_path).name
            if filename:
                return outputs_dir / filename
        return outputs_dir / "refined_output.csv"

    def _update_column_choices(self, headers: List[str], *, prefer_existing: bool = True) -> None:
        self.lat_combo["values"] = headers
        self.lon_combo["values"] = headers

        current_lat = self.lat_column_var.get().strip()
        current_lon = self.lon_column_var.get().strip()

        lat_guess, lon_guess = self._guess_lat_lon(headers)
        if prefer_existing and current_lat in headers:
            self.lat_column_var.set(current_lat)
        elif lat_guess:
            self.lat_column_var.set(lat_guess)
        if prefer_existing and current_lon in headers:
            self.lon_column_var.set(current_lon)
        elif lon_guess:
            self.lon_column_var.set(lon_guess)
        self._request_reference_map_update()

    def _request_reference_map_update(self) -> None:
        if not self._map_supported:
            return
        if self._map_update_after_id is not None:
            try:
                self.root.after_cancel(self._map_update_after_id)
            except tk.TclError:
                pass
        self._map_update_after_id = self.root.after(350, self._schedule_reference_map_update)

    def _schedule_reference_map_update(self) -> None:
        self._map_update_after_id = None

        data_path = self.data_path_var.get().strip()
        kmz_path = self.kmz_path_var.get().strip()
        lat_column = self.lat_column_var.get().strip()
        lon_column = self.lon_column_var.get().strip()

        if not data_path or not kmz_path:
            self._set_map_status("Load crash data and KMZ boundary to preview.")
            return

        if not lat_column or not lon_column:
            self._set_map_status("Select latitude and longitude columns to preview.")
            return

        if not Path(data_path).exists() or not Path(kmz_path).exists():
            self._set_map_status("Waiting for valid crash data and KMZ boundary.")
            return

        self._map_request_id += 1
        request_id = self._map_request_id
        self._set_map_status("Loading map preview...")

        worker = threading.Thread(
            target=self._build_reference_map_preview,
            args=(request_id, data_path, kmz_path, lat_column, lon_column),
            daemon=True,
        )
        worker.start()

    def _build_reference_map_preview(
        self,
        request_id: int,
        data_path: str,
        kmz_path: str,
        lat_column: str,
        lon_column: str,
    ) -> None:
        try:
            boundary = load_kmz_polygon(kmz_path)
            data = read_spreadsheet(data_path)

            refiner = CrashDataRefiner()
            included, _excluded, _invalid, report = refiner.filter_rows_by_boundary(
                data.rows,
                boundary=boundary,
                latitude_column=lat_column,
                longitude_column=lon_column,
                normalize_headers=True,
            )

            lat_key = _normalize_header(lat_column)
            lon_key = _normalize_header(lon_column)
            points = []
            for row in included:
                lat = parse_coordinate(row.get(lat_key))
                lon = parse_coordinate(row.get(lon_key))
                if lat is not None and lon is not None:
                    points.append((lat, lon))

            payload = {
                "request_id": request_id,
                "boundary": boundary,
                "points": points,
                "report": report,
            }
            self._queue.put(
                PipelineMessage(level="map", message="Reference map updated.", payload=payload)
            )
        except Exception as exc:
            self._queue.put(
                PipelineMessage(
                    level="map_error",
                    message=str(exc),
                    payload={"request_id": request_id},
                )
            )

    def _set_map_status(self, text: str) -> None:
        if hasattr(self, "map_status_var"):
            self.map_status_var.set(text)

    def _guess_lat_lon(self, headers: List[str]) -> Tuple[Optional[str], Optional[str]]:
        scored = [(self._score_lat_header(h), h) for h in headers]
        lat_choice = max(scored, default=(0, None))

        scored_lon = [(self._score_lon_header(h), h) for h in headers]
        lon_choice = max(scored_lon, default=(0, None))

        return (lat_choice[1] if lat_choice[0] > 0 else None, lon_choice[1] if lon_choice[0] > 0 else None)

    def _score_lat_header(self, header: str) -> int:
        norm = _normalize_header(header)
        if norm in {"lat", "latitude"}:
            return 100
        if "latitude" in norm:
            return 90
        if norm.startswith("lat_") or norm.endswith("_lat"):
            return 80
        if norm in {"y", "y_coord", "y_coordinate"}:
            return 70
        if "lat" in norm:
            return 50
        return 0

    def _score_lon_header(self, header: str) -> int:
        norm = _normalize_header(header)
        if norm in {"lon", "long", "longitude"}:
            return 100
        if "longitude" in norm:
            return 90
        if norm.startswith(("lon_", "long_")) or norm.endswith(("_lon", "_long")):
            return 80
        if norm in {"x", "x_coord", "x_coordinate"}:
            return 70
        if "lon" in norm or "long" in norm:
            return 50
        return 0

    def _get_label_order(self) -> str:
        selection = self.label_order_var.get().strip()
        return self.label_order_options.get(selection, "west_to_east")

    def _order_and_number_rows(
        self,
        rows: List[Dict[str, Any]],
        *,
        lat_column: str,
        lon_column: str,
        label_order: str,
    ) -> List[Dict[str, Any]]:
        lat_key = _normalize_header(lat_column)
        lon_key = _normalize_header(lon_column)

        indexed: List[Tuple[Tuple[float, float, int] | Tuple[int], Dict[str, Any]]] = []
        for idx, row in enumerate(rows):
            lat = parse_coordinate(row.get(lat_key))
            lon = parse_coordinate(row.get(lon_key))
            if label_order == "south_to_north":
                lat_value = lat if lat is not None else float("inf")
                lon_value = lon if lon is not None else float("inf")
                key = (lat_value, lon_value, idx)
            elif label_order == "west_to_east":
                lon_value = lon if lon is not None else float("inf")
                lat_value = lat if lat is not None else float("inf")
                key = (lon_value, lat_value, idx)
            else:
                key = (idx,)
            indexed.append((key, row))

        indexed.sort(key=lambda item: item[0])
        ordered = [item[1] for item in indexed]
        for number, row in enumerate(ordered, start=1):
            row["kmz_label"] = number
        return ordered

    def _build_output_headers(self, rows: List[Dict[str, Any]]) -> List[str]:
        header_set: set[str] = set()
        for row in rows:
            header_set.update(row.keys())
        headers = sorted(header_set)
        if "kmz_label" in headers:
            headers.remove("kmz_label")
            headers.insert(0, "kmz_label")
        return headers

    def _suggest_output_path(self, input_path: str) -> None:
        input_file = Path(input_path)
        suffix = input_file.suffix or ".csv"
        outputs_dir = self._ensure_outputs_dir()
        suggested = outputs_dir / f"{input_file.stem}_refined{suffix}"
        if not self.output_path_var.get().strip():
            self.output_path_var.set(str(suggested))
            self._update_invalid_path_label()

    def _invalid_output_path(self, output_path: Path) -> Path:
        return output_path.with_name(f"Crashes Without Valid Lat-Long Data{output_path.suffix}")

    def _kmz_output_path(self, output_path: Path) -> Path:
        base_name = output_path.stem
        if base_name.lower().endswith("_refined"):
            base_name = base_name[:-8]
        return output_path.with_name(f"{base_name}_Crash Data.kmz")

    def _pdf_output_path(self, output_path: Path) -> Path:
        base_name = output_path.stem
        if base_name.lower().endswith("_refined"):
            base_name = base_name[:-8]
        return output_path.with_name(f"{base_name}_Crash Data Full Report.pdf")


    def _on_run(self) -> None:
        data_path = self.data_path_var.get().strip()
        kmz_path = self.kmz_path_var.get().strip()
        output_path = self.output_path_var.get().strip()
        lat_column = self.lat_column_var.get().strip()
        lon_column = self.lon_column_var.get().strip()
        label_order = self._get_label_order()

        if not data_path:
            messagebox.showwarning("Crash Data Refiner", "Select a crash data file to continue.")
            return
        if not kmz_path:
            messagebox.showwarning("Crash Data Refiner", "Select a KMZ polygon file to continue.")
            return
        if not output_path:
            messagebox.showwarning("Crash Data Refiner", "Select a refined output file path.")
            return
        if not lat_column or not lon_column:
            messagebox.showwarning("Crash Data Refiner", "Select latitude and longitude columns.")
            return
        resolved_output = self._resolve_output_path(output_path)
        if str(resolved_output) != output_path:
            self.output_path_var.set(str(resolved_output))
            output_path = str(resolved_output)

        self._append_log("Starting refinement pipeline...")
        self.run_button.configure(state=tk.DISABLED)
        self.generate_report_button.configure(state=tk.DISABLED)
        self.open_folder_button.configure(state=tk.DISABLED)
        self.open_pdf_button.configure(state=tk.DISABLED)
        self.progress.start(10)
        self.report_progress.stop()
        self._last_pdf_path = None

        worker = threading.Thread(
            target=self._run_pipeline,
            args=(
                data_path,
                kmz_path,
                output_path,
                lat_column,
                lon_column,
                label_order,
            ),
            daemon=True,
        )
        worker.start()

    def _on_generate_report(self) -> None:
        output_path = self.output_path_var.get().strip()
        pdf_data_path = self.pdf_data_path_var.get().strip()

        resolved_output = self._resolve_output_path(output_path)
        pdf_source = Path(pdf_data_path) if pdf_data_path else resolved_output
        if not pdf_source.exists():
            messagebox.showwarning(
                "Crash Data Refiner",
                "PDF report data file not found. Run refinement or select a PDF data file.",
            )
            return

        lat_column = self.lat_column_var.get().strip()
        lon_column = self.lon_column_var.get().strip()
        if not lat_column or not lon_column:
            try:
                headers = read_spreadsheet_headers(str(pdf_source))
            except Exception as exc:
                messagebox.showerror("Crash Data Refiner", f"Failed to read headers: {exc}")
                return
            lat_guess, lon_guess = self._guess_lat_lon(headers)
            if not lat_column and lat_guess:
                lat_column = lat_guess
                self.lat_column_var.set(lat_guess)
            if not lon_column and lon_guess:
                lon_column = lon_guess
                self.lon_column_var.set(lon_guess)
            self._update_column_choices(headers, prefer_existing=True)

        if not lat_column or not lon_column:
            messagebox.showwarning(
                "Crash Data Refiner",
                "Select latitude and longitude columns or ensure the report file includes them.",
            )
            return

        pdf_path = self._pdf_output_path(resolved_output)

        self._append_log("Generating PDF crash report...")
        self.run_button.configure(state=tk.DISABLED)
        self.generate_report_button.configure(state=tk.DISABLED)
        self.open_pdf_button.configure(state=tk.DISABLED)
        self.report_progress.start(10)
        self._last_pdf_path = None

        worker = threading.Thread(
            target=self._run_report_generation,
            args=(str(pdf_source), str(pdf_path), lat_column, lon_column),
            daemon=True,
        )
        worker.start()

    def _run_pipeline(
        self,
        data_path: str,
        kmz_path: str,
        output_path: str,
        lat_column: str,
        lon_column: str,
        label_order: str,
    ) -> None:
        try:
            boundary = load_kmz_polygon(kmz_path)
            data = read_spreadsheet(data_path)

            refiner = CrashDataRefiner()
            refined_rows, report, boundary_report, invalid_rows = refiner.refine_rows_with_boundary(
                data.rows,
                boundary=boundary,
                latitude_column=lat_column,
                longitude_column=lon_column,
            )
            refined_rows = self._order_and_number_rows(
                refined_rows,
                lat_column=lat_column,
                lon_column=lon_column,
                label_order=label_order,
            )

            output_file = self._resolve_output_path(output_path)
            output_headers = self._build_output_headers(refined_rows)
            write_spreadsheet(str(output_file), refined_rows, headers=output_headers)

            invalid_path = self._invalid_output_path(output_file)
            write_spreadsheet(str(invalid_path), invalid_rows)

            kmz_path = self._kmz_output_path(output_file)
            kmz_count = write_kmz_report(
                str(kmz_path),
                rows=refined_rows,
                latitude_column=lat_column,
                longitude_column=lon_column,
                label_order=label_order,
            )

            payload = {
                "included": boundary_report.included_rows,
                "excluded": boundary_report.excluded_rows,
                "invalid": boundary_report.invalid_rows,
                "kmz_path": str(kmz_path),
                "kmz_count": kmz_count,
                "output_folder": str(self._ensure_outputs_dir()),
            }
            self._queue.put(PipelineMessage(level="success", message="Refinement complete.", payload=payload))
        except Exception as exc:
            self._queue.put(PipelineMessage(level="error", message=str(exc)))

    def _run_report_generation(
        self,
        pdf_source: str,
        pdf_path: str,
        lat_column: str,
        lon_column: str,
    ) -> None:
        try:
            pdf_data = read_spreadsheet(pdf_source)
            generate_pdf_report(
                pdf_path,
                rows=pdf_data.rows,
                latitude_column=lat_column,
                longitude_column=lon_column,
            )
            payload = {
                "pdf_path": pdf_path,
                "output_folder": str(self._ensure_outputs_dir()),
            }
            self._queue.put(PipelineMessage(level="pdf_success", message="PDF report generated.", payload=payload))
        except Exception as exc:
            self._queue.put(PipelineMessage(level="pdf_error", message=str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                message = self._queue.get_nowait()
                if message.level == "success" and message.payload:
                    self._handle_success(message)
                elif message.level == "error":
                    self._handle_error(message)
                elif message.level == "pdf_success":
                    self._handle_pdf_success(message)
                elif message.level == "pdf_error":
                    self._handle_pdf_error(message)
                elif message.level == "map":
                    self._handle_reference_map_update(message)
                elif message.level == "map_error":
                    self._handle_reference_map_error(message)
                else:
                    self._append_log(message.message)
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _handle_success(self, message: PipelineMessage) -> None:
        payload = message.payload or {}
        self.included_var.set(str(payload.get("included", 0)))
        self.excluded_var.set(str(payload.get("excluded", 0)))
        self.invalid_var.set(str(payload.get("invalid", 0)))
        self._append_log(message.message)

        kmz_path = payload.get("kmz_path")
        kmz_count = payload.get("kmz_count")
        if kmz_path:
            count_text = f" ({kmz_count} placemarks)" if kmz_count is not None else ""
            self._append_log(f"KMZ output saved: {kmz_path}{count_text}")

        pdf_path = payload.get("pdf_path")
        if pdf_path:
            self._last_pdf_path = Path(pdf_path)
            self._append_log(f"Full crash report PDF saved: {pdf_path}")
            self.open_pdf_button.configure(state=tk.NORMAL)
        else:
            self._last_pdf_path = None
            self.open_pdf_button.configure(state=tk.DISABLED)

        output_folder = payload.get("output_folder")
        if output_folder:
            self.open_folder_button.configure(state=tk.NORMAL)

        self.run_button.configure(state=tk.NORMAL)
        self.generate_report_button.configure(state=tk.NORMAL)
        self.progress.stop()
        self.report_progress.stop()

    def _handle_error(self, message: PipelineMessage) -> None:
        self._append_log(f"Error: {message.message}")
        self.run_button.configure(state=tk.NORMAL)
        self.generate_report_button.configure(state=tk.NORMAL)
        self.progress.stop()
        self.report_progress.stop()
        self.open_pdf_button.configure(state=tk.DISABLED)
        messagebox.showerror("Crash Data Refiner", message.message)

    def _handle_pdf_success(self, message: PipelineMessage) -> None:
        payload = message.payload or {}
        self._append_log(message.message)

        pdf_path = payload.get("pdf_path")
        if pdf_path:
            self._last_pdf_path = Path(pdf_path)
            self._append_log(f"Full crash report PDF saved: {pdf_path}")
            self.open_pdf_button.configure(state=tk.NORMAL)
        else:
            self._last_pdf_path = None
            self.open_pdf_button.configure(state=tk.DISABLED)

        output_folder = payload.get("output_folder")
        if output_folder:
            self.open_folder_button.configure(state=tk.NORMAL)

        self.run_button.configure(state=tk.NORMAL)
        self.generate_report_button.configure(state=tk.NORMAL)
        self.progress.stop()
        self.report_progress.stop()

    def _handle_pdf_error(self, message: PipelineMessage) -> None:
        self._append_log(f"Error: {message.message}")
        self.run_button.configure(state=tk.NORMAL)
        self.generate_report_button.configure(state=tk.NORMAL)
        self.progress.stop()
        self.report_progress.stop()
        self.open_pdf_button.configure(state=tk.DISABLED)
        messagebox.showerror("Crash Data Refiner", message.message)

    def _handle_reference_map_update(self, message: PipelineMessage) -> None:
        payload = message.payload or {}
        request_id = payload.get("request_id")
        if request_id != self._map_request_id:
            return

        boundary = payload.get("boundary")
        points = payload.get("points", [])
        report = payload.get("report")

        self._update_reference_map(boundary, points)

        if report:
            self._set_map_status(
                "Included: "
                f"{report.included_rows} | Excluded: {report.excluded_rows} | Without Lat/Long Data: {report.invalid_rows}"
            )
        else:
            self._set_map_status(f"{len(points)} points loaded.")

    def _handle_reference_map_error(self, message: PipelineMessage) -> None:
        payload = message.payload or {}
        request_id = payload.get("request_id")
        if request_id != self._map_request_id:
            return
        self._set_map_status(f"Reference map unavailable: {message.message}")

    def _update_reference_map(
        self,
        boundary: Any,
        points: List[Tuple[float, float]],
    ) -> None:
        if not self.map_widget:
            return

        self._clear_reference_map()

        if boundary:
            positions = [(lat, lon) for lon, lat in boundary.outer]
            if positions:
                self._map_polygon = self._draw_reference_polygon(positions)
                min_lon, min_lat, max_lon, max_lat = boundary.bbox
                center_lat = (min_lat + max_lat) / 2
                center_lon = (min_lon + max_lon) / 2
                self.map_widget.set_position(center_lat, center_lon)
                self.map_widget.set_zoom(self._estimate_zoom(boundary))

        for lat, lon in points:
            marker = self.map_widget.set_marker(lat, lon, text="")
            self._map_markers.append(marker)

    def _clear_reference_map(self) -> None:
        for marker in self._map_markers:
            try:
                marker.delete()
            except Exception:
                pass
        self._map_markers = []

        if self._map_polygon:
            try:
                self._map_polygon.delete()
            except Exception:
                pass
            self._map_polygon = None

    def _draw_reference_polygon(self, positions: List[Tuple[float, float]]) -> Any:
        if not self.map_widget:
            return None
        if hasattr(self.map_widget, "set_polygon"):
            return self.map_widget.set_polygon(
                positions,
                outline_color=self._palette["accent"],
                fill_color=self._palette["accent_soft"],
                border_width=2,
            )
        if positions and positions[0] != positions[-1]:
            positions = positions + [positions[0]]
        return self.map_widget.set_path(
            positions,
            color=self._palette["accent"],
            width=2,
        )

    def _estimate_zoom(self, boundary: Any) -> int:
        min_lon, min_lat, max_lon, max_lat = boundary.bbox
        span = max(max_lon - min_lon, max_lat - min_lat)
        if span <= 0:
            return 12
        zoom = int(round(math.log2(360 / span)))
        return max(3, min(18, zoom))

    def _append_log(self, text: str) -> None:
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{text}\n")
        self.log_widget.configure(state=tk.DISABLED)
        self.log_widget.see(tk.END)

    def _open_output_folder(self) -> None:
        folder = self._ensure_outputs_dir()
        if folder.exists():
            try:
                import os

                os.startfile(str(folder))  # type: ignore[attr-defined]
            except Exception:
                try:
                    folder_uri = folder.as_uri()
                except ValueError:
                    folder_uri = str(folder)
                webbrowser.open(folder_uri)

    def _open_pdf_report(self) -> None:
        if not self._last_pdf_path:
            return
        pdf_path = self._last_pdf_path
        if not pdf_path.exists():
            messagebox.showwarning(
                "Crash Data Refiner",
                f"PDF report not found: {pdf_path}",
            )
            return
        try:
            import os

            os.startfile(str(pdf_path))  # type: ignore[attr-defined]
        except Exception:
            try:
                pdf_uri = pdf_path.as_uri()
            except ValueError:
                pdf_uri = str(pdf_path)
            webbrowser.open(pdf_uri)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = CrashRefinerApp()
    app.run()


if __name__ == "__main__":
    main()

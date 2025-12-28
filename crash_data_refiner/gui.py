"""Desktop GUI for CrashDataRefiner."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional, Tuple
import webbrowser

from .geo import load_kmz_polygon, parse_coordinate
from .map_report import write_map_report
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
        self._last_map_report: Optional[Path] = None

        self._configure_theme()
        self._build_layout()
        self._ensure_window_size()
        self.root.after(200, self._poll_queue)

    def _ensure_window_size(self) -> None:
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        req_width = max(self.root.winfo_reqwidth(), 1100)
        req_height = max(self.root.winfo_reqheight(), 820)

        target_width = min(req_width, int(screen_width * 0.95))
        target_height = min(req_height, int(screen_height * 0.9))

        x = max((screen_width - target_width) // 2, 0)
        y = max((screen_height - target_height) // 2, 0)
        self.root.geometry(f"{int(target_width)}x{int(target_height)}+{int(x)}+{int(y)}")

        min_width = min(int(target_width), int(screen_width * 0.9))
        min_height = min(int(target_height), int(screen_height * 0.85))
        self.root.minsize(min_width, min_height)

    def _configure_theme(self) -> None:
        try:
            self.root.tk.call("tk", "scaling", 1.2)
        except tk.TclError:
            pass

        palette = {
            "base": "#0d1117",
            "surface": "#0b1220",
            "surface_alt": "#0f172a",
            "card": "#111827",
            "overlay": "#111827",
            "field": "#0f172a",
            "field_hover": "#16223b",
            "field_active": "#1e335a",
            "border": "#24384b",
            "outline": "#2c3b50",
            "accent": "#58a6ff",
            "accent_active": "#79b8ff",
            "accent_pressed": "#1f6feb",
            "accent_dim": "#244a74",
            "accent_soft": "#0c2d50",
            "success": "#2ea043",
            "warning": "#d29922",
            "error": "#f85149",
            "text": "#e6edf3",
            "muted": "#9aa7b2",
            "muted_alt": "#7d8590",
            "code_bg": "#161b22",
            "hero_start": "#0d1117",
            "hero_end": "#0d1117",
            "hero_gloss": "#0d1117",
        }
        self._palette = palette

        self.root.configure(background=palette["base"])
        default_font = "{Segoe UI} 11"
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
        style.configure("Card.TFrame", background=palette["card"])
        style.configure("CardBody.TFrame", background=palette["card"])
        style.configure("Glass.TFrame", background=palette["surface_alt"], relief=tk.FLAT)
        style.configure("Header.TFrame", background=palette["hero_start"])
        style.configure("TLabel", background=palette["card"], foreground=palette["text"])
        style.configure(
            "Heading.TLabel",
            background=palette["card"],
            foreground=palette["text"],
            font=("Segoe UI Semibold", 18),
        )
        style.configure(
            "Subheading.TLabel",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            font=("Segoe UI", 11),
        )
        style.configure(
            "Body.TLabel",
            background=palette["surface_alt"],
            foreground=palette["text"],
            font=("Segoe UI", 11),
        )
        style.configure(
            "SectionHeading.TLabel",
            background=palette["card"],
            foreground=palette["text"],
            font=("Segoe UI Semibold", 14),
        )
        style.configure(
            "Hint.TLabel",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
            wraplength=320,
        )
        style.configure(
            "MetricValue.TLabel",
            background=palette["surface_alt"],
            foreground=palette["text"],
            font=("Segoe UI Semibold", 22),
        )
        style.configure(
            "MetricCaption.TLabel",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Primary.TButton",
            background=palette["accent_pressed"],
            foreground=palette["text"],
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", palette["accent"]),
                ("pressed", palette["accent_pressed"]),
                ("disabled", palette["accent_dim"]),
            ],
        )
        style.configure(
            "Secondary.TButton",
            background=palette["surface_alt"],
            foreground=palette["text"],
        )
        style.map(
            "Secondary.TButton",
            background=[("active", palette["field_hover"]), ("pressed", palette["field_active"])],
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
            font=("Segoe UI Semibold", 24),
        )
        header.create_window(32, 30, anchor="nw", window=header_title)
        header_subtitle = tk.Label(
            header,
            text="KMZ Relevance Boundary + refined crash outputs",
            bg=self._palette["hero_start"],
            fg=self._palette["muted"],
            font=("Segoe UI", 12),
        )
        header.create_window(34, 68, anchor="nw", window=header_subtitle)

        body = ttk.Frame(container, style="Background.TFrame", padding=(24, 18, 24, 24))
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        self._build_inputs(body)
        self._build_status(body)

    def _build_inputs(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(16, 12))
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Project Inputs", style="SectionHeading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        self.data_path_var = tk.StringVar()
        self.kmz_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.lat_column_var = tk.StringVar()
        self.lon_column_var = tk.StringVar()
        self.invalid_path_var = tk.StringVar()

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
            label="KMZ Polygon",
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
        current_row += 1

        ttk.Label(card, text="Longitude Column", style="Body.TLabel").grid(
            row=current_row, column=0, sticky="w"
        )
        current_row += 1
        self.lon_combo = ttk.Combobox(card, textvariable=self.lon_column_var, state="readonly")
        self.lon_combo.grid(row=current_row, column=0, sticky="ew", pady=(4, 8))
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
        self._update_invalid_path_label()

    def _build_status(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(20, 18))
        card.grid(row=0, column=1, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        ttk.Label(card, text="Run Summary", style="SectionHeading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        summary = ttk.Frame(card, style="Glass.TFrame", padding=(16, 14))
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)
        summary.columnconfigure(2, weight=1)

        self.included_var = tk.StringVar(value="0")
        self.excluded_var = tk.StringVar(value="0")
        self.invalid_var = tk.StringVar(value="0")

        self._add_metric(summary, "Included", self.included_var, 0)
        self._add_metric(summary, "Excluded", self.excluded_var, 1)
        self._add_metric(summary, "Invalid Lat/Long", self.invalid_var, 2)

        log_frame = ttk.Frame(card, style="Glass.TFrame", padding=(12, 12))
        log_frame.grid(row=2, column=0, sticky="nsew")
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
        action_row.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)

        self.map_button = ttk.Button(
            action_row,
            text="Open Map Report",
            style="Secondary.TButton",
            command=self._open_map_report,
            state=tk.DISABLED,
        )
        self.map_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.open_folder_button = ttk.Button(
            action_row,
            text="Open Output Folder",
            style="Secondary.TButton",
            command=self._open_output_folder,
            state=tk.DISABLED,
        )
        self.open_folder_button.grid(row=0, column=1, sticky="ew")

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
            path = filedialog.asksaveasfilename(filetypes=filetypes)
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
        return

    def _on_select_output_file(self) -> None:
        self._update_invalid_path_label()

    def _update_invalid_path_label(self) -> None:
        output_path = self.output_path_var.get().strip()
        if not output_path:
            self.invalid_path_var.set("Invalid coordinate output will be created next to the refined file.")
            return
        invalid_path = self._invalid_output_path(Path(output_path))
        self.invalid_path_var.set(f"Invalid coordinate output: {invalid_path}")

    def _update_column_choices(self, headers: List[str]) -> None:
        self.lat_combo["values"] = headers
        self.lon_combo["values"] = headers

        lat_guess, lon_guess = self._guess_lat_lon(headers)
        if lat_guess:
            self.lat_column_var.set(lat_guess)
        if lon_guess:
            self.lon_column_var.set(lon_guess)

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

    def _suggest_output_path(self, input_path: str) -> None:
        input_file = Path(input_path)
        suffix = input_file.suffix or ".csv"
        suggested = input_file.with_name(f"{input_file.stem}_refined{suffix}")
        if not self.output_path_var.get().strip():
            self.output_path_var.set(str(suggested))
            self._update_invalid_path_label()

    def _invalid_output_path(self, output_path: Path) -> Path:
        return output_path.with_name(f"Crashes Without Valid Lat-Long Data{output_path.suffix}")

    def _on_run(self) -> None:
        data_path = self.data_path_var.get().strip()
        kmz_path = self.kmz_path_var.get().strip()
        output_path = self.output_path_var.get().strip()
        lat_column = self.lat_column_var.get().strip()
        lon_column = self.lon_column_var.get().strip()

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

        self._append_log("Starting refinement pipeline...")
        self.run_button.configure(state=tk.DISABLED)
        self.map_button.configure(state=tk.DISABLED)
        self.open_folder_button.configure(state=tk.DISABLED)
        self.progress.start(10)

        worker = threading.Thread(
            target=self._run_pipeline,
            args=(data_path, kmz_path, output_path, lat_column, lon_column),
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

            output_file = Path(output_path)
            write_spreadsheet(str(output_file), refined_rows)

            invalid_path = self._invalid_output_path(output_file)
            write_spreadsheet(str(invalid_path), invalid_rows)

            lat_norm = _normalize_header(lat_column)
            lon_norm = _normalize_header(lon_column)
            points = []
            for row in refined_rows:
                lat = parse_coordinate(row.get(lat_norm))
                lon = parse_coordinate(row.get(lon_norm))
                if lat is not None and lon is not None:
                    points.append((lat, lon))

            map_report_path = output_file.with_name("Crash Data Refiner Map Report.html")
            write_map_report(
                str(map_report_path),
                polygon=boundary,
                points=points,
                included_count=boundary_report.included_rows,
                excluded_count=boundary_report.excluded_rows,
                invalid_count=boundary_report.invalid_rows,
            )

            payload = {
                "included": boundary_report.included_rows,
                "excluded": boundary_report.excluded_rows,
                "invalid": boundary_report.invalid_rows,
                "map_report": map_report_path,
                "output_folder": output_file.parent,
            }
            self._queue.put(PipelineMessage(level="success", message="Refinement complete.", payload=payload))
        except Exception as exc:
            self._queue.put(PipelineMessage(level="error", message=str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                message = self._queue.get_nowait()
                if message.level == "success" and message.payload:
                    self._handle_success(message)
                elif message.level == "error":
                    self._handle_error(message)
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

        map_report = payload.get("map_report")
        if map_report:
            self._last_map_report = Path(map_report)
            self.map_button.configure(state=tk.NORMAL)

        output_folder = payload.get("output_folder")
        if output_folder:
            self.open_folder_button.configure(state=tk.NORMAL)

        self.run_button.configure(state=tk.NORMAL)
        self.progress.stop()

        if self._last_map_report and self._last_map_report.exists():
            webbrowser.open(self._last_map_report.as_uri())

    def _handle_error(self, message: PipelineMessage) -> None:
        self._append_log(f"Error: {message.message}")
        self.run_button.configure(state=tk.NORMAL)
        self.progress.stop()
        messagebox.showerror("Crash Data Refiner", message.message)

    def _append_log(self, text: str) -> None:
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{text}\n")
        self.log_widget.configure(state=tk.DISABLED)
        self.log_widget.see(tk.END)

    def _open_map_report(self) -> None:
        if self._last_map_report and self._last_map_report.exists():
            webbrowser.open(self._last_map_report.as_uri())

    def _open_output_folder(self) -> None:
        output_path = self.output_path_var.get().strip()
        if not output_path:
            return
        folder = Path(output_path).parent
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

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = CrashRefinerApp()
    app.run()


if __name__ == "__main__":
    main()

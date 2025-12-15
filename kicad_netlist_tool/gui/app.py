"""KiCad Netlist Tool GUI - CustomTkinter with columns layout."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import time
from typing import Optional, Dict, Tuple

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

from ..tokn import (
    find_project_root,
    parse_hierarchical_schematic,
    HierarchicalSchematic,
    Schematic,
    encode_sheet_tokn,
)

# Use system theme
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class SheetTreeView(ctk.CTkScrollableFrame):
    """Scrollable frame with checkboxes for sheet selection."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.check_vars: Dict[str, ctk.BooleanVar] = {}
        self.sheet_data: Dict[str, Tuple[str, Schematic]] = {}

    def clear(self):
        """Clear all checkboxes."""
        for widget in self.winfo_children():
            widget.destroy()
        self.checkboxes.clear()
        self.check_vars.clear()
        self.sheet_data.clear()

    def load_hierarchy(self, hier: HierarchicalSchematic):
        """Load sheets from hierarchy."""
        self.clear()

        for i, (hier_path, schematic) in enumerate(hier.sheets):
            # Get display name with indentation based on path depth
            depth = hier_path.count('_')
            display_name = schematic.title or schematic.filename or hier_path.split('_')[-1]
            if hier_path == hier.project_name:
                display_name = f"{hier.project_name} (root)"

            # Create checkbox
            var = ctk.BooleanVar(value=True)
            indent = "    " * depth
            cb = ctk.CTkCheckBox(
                self,
                text=f"{indent}{display_name}",
                variable=var,
                font=ctk.CTkFont(size=13),
                height=28
            )
            cb.pack(anchor="w", pady=1, padx=5)

            self.checkboxes[hier_path] = cb
            self.check_vars[hier_path] = var
            self.sheet_data[hier_path] = (hier_path, schematic)

    def select_all(self):
        """Select all sheets."""
        for var in self.check_vars.values():
            var.set(True)

    def select_none(self):
        """Deselect all sheets."""
        for var in self.check_vars.values():
            var.set(False)

    def get_selected_sheets(self):
        """Get list of selected (hier_path, schematic) tuples."""
        return [
            self.sheet_data[path]
            for path, var in self.check_vars.items()
            if var.get()
        ]


class KiCadApp(ctk.CTk):
    """Main application window with two-column layout."""

    def __init__(self):
        super().__init__()

        self.title("KiCad Netlist Tool")
        self.geometry("900x650")
        self.minsize(800, 550)

        # State
        self.project_path: Optional[Path] = None
        self.hierarchy: Optional[HierarchicalSchematic] = None
        self.monitoring = False
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._countdown_job = None
        self._next_check_time = 0.0
        self._loading_job = None
        self._loading_dots = 0

        self._setup_ui()

    def _setup_ui(self):
        """Setup the two-column UI."""
        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)

        # Two columns: left (60%) and right (40%)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        # === LEFT COLUMN ===
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Project section
        proj_frame = ctk.CTkFrame(left)
        proj_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        proj_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(proj_frame, text="Project", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

        # Path entry row
        path_row = ctk.CTkFrame(proj_frame, fg_color="transparent")
        path_row.pack(fill="x", padx=10, pady=(0, 5))

        self.project_var = ctk.StringVar()
        self.project_entry = ctk.CTkEntry(path_row, textvariable=self.project_var, height=32)
        self.project_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.project_entry.bind('<Return>', lambda e: self._load_project_from_entry())

        ctk.CTkButton(path_row, text="Browse", width=80, height=32, command=self._browse_project).pack(side="right")

        # Quick buttons
        quick_row = ctk.CTkFrame(proj_frame, fg_color="transparent")
        quick_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(quick_row, text="Examples", width=80, height=28, command=self._go_examples).pack(side="left", padx=(0, 5))
        ctk.CTkButton(quick_row, text="Home", width=80, height=28, command=self._go_home).pack(side="left", padx=(0, 5))
        ctk.CTkButton(quick_row, text="Current", width=80, height=28, command=self._go_cwd).pack(side="left")

        # Sheets section
        sheets_frame = ctk.CTkFrame(left)
        sheets_frame.grid(row=1, column=0, sticky="nsew")
        sheets_frame.grid_rowconfigure(1, weight=1)
        sheets_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sheets_frame, text="Sheets", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        self.sheet_tree = SheetTreeView(sheets_frame, fg_color="transparent")
        self.sheet_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 5))

        # Selection buttons
        sel_row = ctk.CTkFrame(sheets_frame, fg_color="transparent")
        sel_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        ctk.CTkButton(sel_row, text="Select All", width=90, height=28, command=self.sheet_tree.select_all).pack(side="left", padx=(0, 5))
        ctk.CTkButton(sel_row, text="Select None", width=90, height=28, command=self.sheet_tree.select_none).pack(side="left")

        # === RIGHT COLUMN ===
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        # Statistics section
        stats_frame = ctk.CTkFrame(right)
        stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        stats_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(stats_frame, text="Statistics", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

        stats_content = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_content.pack(fill="x", padx=10, pady=(0, 10))

        # Stats grid
        self.stats_labels = {}
        stats_data = [
            ("sheets", "Sheets:"),
            ("components", "Components:"),
            ("nets", "Wires:"),
            ("original", "Original:"),
            ("tokn", "TOKN:"),
            ("reduction", "Reduction:"),
        ]

        for i, (key, label) in enumerate(stats_data):
            row = i // 2
            col = (i % 2) * 2

            ctk.CTkLabel(stats_content, text=label, font=ctk.CTkFont(size=12)).grid(row=row, column=col, sticky="w", padx=(0, 5), pady=2)
            val_label = ctk.CTkLabel(stats_content, text="-", font=ctk.CTkFont(size=12, weight="bold"))
            val_label.grid(row=row, column=col + 1, sticky="w", padx=(0, 15), pady=2)
            self.stats_labels[key] = val_label

        # Output section
        output_frame = ctk.CTkFrame(right)
        output_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        output_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(output_frame, text="Output", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

        # Filename row
        file_row = ctk.CTkFrame(output_frame, fg_color="transparent")
        file_row.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(file_row, text="Filename:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.output_var = ctk.StringVar(value="netlist.tokn")
        ctk.CTkEntry(file_row, textvariable=self.output_var, width=150, height=28).pack(side="left", padx=(5, 0))

        # Action buttons
        btn_row = ctk.CTkFrame(output_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkButton(btn_row, text="Copy to Clipboard", height=36, command=self._copy_to_clipboard).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="Save to File", height=36, command=self._save_to_file).pack(side="left")

        # Monitoring section
        monitor_frame = ctk.CTkFrame(right)
        monitor_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        monitor_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(monitor_frame, text="Monitoring", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

        mon_row = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        mon_row.pack(fill="x", padx=10, pady=(0, 10))

        self.watch_button = ctk.CTkButton(mon_row, text="Start Watching", width=130, height=32, command=self._toggle_monitoring)
        self.watch_button.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(mon_row, text="Interval:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.interval_var = ctk.StringVar(value="60")
        ctk.CTkEntry(mon_row, textvariable=self.interval_var, width=50, height=28).pack(side="left", padx=(5, 0))
        ctk.CTkLabel(mon_row, text="sec", font=ctk.CTkFont(size=12)).pack(side="left", padx=(5, 0))

        # Status bar (at bottom of right column)
        status_frame = ctk.CTkFrame(right)
        status_frame.grid(row=3, column=0, sticky="sew")
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_var = ctk.StringVar(value="Select a project directory")
        self.status_label = ctk.CTkLabel(status_frame, textvariable=self.status_var, font=ctk.CTkFont(size=12))
        self.status_label.pack(anchor="w", padx=10, pady=10)

        # Make status stick to bottom
        right.grid_rowconfigure(3, weight=1)

    def _browse_project(self):
        """Open directory browser."""
        initial = str(self.project_path) if self.project_path else str(Path.home())
        directory = filedialog.askdirectory(title="Select KiCad Project Directory", initialdir=initial)
        if directory:
            self._load_project(Path(directory))

    def _load_project_from_entry(self):
        """Load project from entry field."""
        path_str = self.project_var.get().strip()
        if path_str:
            path = Path(path_str).expanduser().resolve()
            if path.exists() and path.is_dir():
                self._load_project(path)
            else:
                messagebox.showerror("Error", f"Directory not found: {path}")

    def _load_project(self, path: Path):
        """Load a KiCad project (non-blocking)."""
        # Update UI immediately and start loading animation
        self.project_path = path
        self.project_var.set(str(path))
        self._loading_dots = 0
        self._update_loading_status()

        # Do all heavy work in background thread
        def parse_async():
            try:
                root_sch, project_name = find_project_root(path)
                if not root_sch:
                    self.after(0, lambda: self._on_no_project_found(path))
                    return

                hierarchy = parse_hierarchical_schematic(str(root_sch))
                # Update UI on main thread
                self.after(0, lambda: self._on_project_loaded(hierarchy, project_name))
            except Exception as e:
                self.after(0, lambda: self._on_project_error(e))

        threading.Thread(target=parse_async, daemon=True).start()

    def _on_no_project_found(self, path: Path):
        """Called when no project is found."""
        self._stop_loading_animation()
        messagebox.showwarning("No Project Found", f"No KiCad schematic files found in:\n{path}")
        self.status_var.set("No project found")

    def _update_loading_status(self):
        """Animate loading status."""
        dots = "." * (self._loading_dots % 4)
        self.status_var.set(f"Loading{dots}")
        self._loading_dots += 1
        self._loading_job = self.after(300, self._update_loading_status)

    def _stop_loading_animation(self):
        """Stop the loading animation."""
        if self._loading_job:
            self.after_cancel(self._loading_job)
            self._loading_job = None

    def _on_project_loaded(self, hierarchy: HierarchicalSchematic, project_name: str):
        """Called when project parsing completes."""
        self._stop_loading_animation()
        self.hierarchy = hierarchy
        self.sheet_tree.load_hierarchy(self.hierarchy)
        self._update_statistics()
        self.status_var.set(f"Loaded: {project_name}")

    def _on_project_error(self, error: Exception):
        """Called when project parsing fails."""
        self._stop_loading_animation()
        messagebox.showerror("Parse Error", f"Failed to parse schematic:\n{error}")
        self.status_var.set(f"Error: {error}")

    def _update_statistics(self):
        """Update the statistics display."""
        if not self.hierarchy:
            return

        selected = self.sheet_tree.get_selected_sheets()

        sheet_count = len(selected)
        comp_count = sum(len(s.components) for _, s in selected)
        wire_count = sum(len(s.wires) for _, s in selected)

        self.stats_labels["sheets"].configure(text=str(sheet_count))
        self.stats_labels["components"].configure(text=str(comp_count))
        self.stats_labels["nets"].configure(text=str(wire_count))

        # Calculate token counts
        tokn_output = self._generate_tokn()
        if tokn_output and HAS_TIKTOKEN:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
                tokn_tokens = len(enc.encode(tokn_output))

                # Estimate original tokens (rough: ~1 token per 4 chars of kicad_sch)
                original_size = sum(
                    len(s.raw_content) if hasattr(s, 'raw_content') else len(str(s.components)) * 50
                    for _, s in selected
                )
                original_tokens = original_size // 4

                if original_tokens > 0:
                    reduction = (1 - tokn_tokens / original_tokens) * 100
                    self.stats_labels["original"].configure(text=f"{original_tokens:,}")
                    self.stats_labels["tokn"].configure(text=f"{tokn_tokens:,}")
                    self.stats_labels["reduction"].configure(text=f"{reduction:.1f}%")
                else:
                    self.stats_labels["original"].configure(text="-")
                    self.stats_labels["tokn"].configure(text=f"{tokn_tokens:,}")
                    self.stats_labels["reduction"].configure(text="-")
            except Exception:
                self.stats_labels["original"].configure(text="-")
                self.stats_labels["tokn"].configure(text="-")
                self.stats_labels["reduction"].configure(text="-")
        else:
            self.stats_labels["original"].configure(text="-")
            self.stats_labels["tokn"].configure(text="-")
            self.stats_labels["reduction"].configure(text="-")

    def _go_examples(self):
        """Navigate to examples directory."""
        import kicad_netlist_tool
        examples_dir = Path(kicad_netlist_tool.__file__).parent.parent / "examples"
        if examples_dir.exists():
            self._load_project(examples_dir)
        else:
            messagebox.showwarning("Not Found", "Examples directory not found")

    def _go_home(self):
        """Navigate to home directory."""
        self.project_var.set(str(Path.home()))
        self._load_project_from_entry()

    def _go_cwd(self):
        """Navigate to current directory."""
        self.project_var.set(str(Path.cwd()))
        self._load_project_from_entry()

    def _generate_tokn(self) -> Optional[str]:
        """Generate TOKN output for selected sheets."""
        if not self.hierarchy:
            return None

        selected = self.sheet_tree.get_selected_sheets()
        if not selected:
            return None

        lines = ['# TOKN v1']
        lines.append(f'project: {self.hierarchy.project_name}')
        lines.append(f'sheets: {len(selected)}')
        lines.append('')

        for hier_path, schematic in selected:
            lines.append(f'# sheet: {hier_path}')
            if schematic.title:
                lines.append(f'# title: {schematic.title}')
            lines.append('')

            sheet_tokn = encode_sheet_tokn(schematic)
            if sheet_tokn:
                lines.append(sheet_tokn)
            lines.append('')

        return '\n'.join(lines)

    def _copy_to_clipboard(self):
        """Copy TOKN to clipboard."""
        if not self.hierarchy:
            messagebox.showwarning("No Project", "Please load a project first")
            return

        selected = self.sheet_tree.get_selected_sheets()
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one sheet")
            return

        tokn = self._generate_tokn()
        if tokn:
            self.clipboard_clear()
            self.clipboard_append(tokn)
            self._update_statistics()
            self.status_var.set(f"Copied {len(selected)} sheet(s) to clipboard")

    def _save_to_file(self):
        """Save TOKN to file."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first")
            return

        selected = self.sheet_tree.get_selected_sheets()
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one sheet")
            return

        tokn = self._generate_tokn()
        if tokn:
            output_path = self.project_path / self.output_var.get()
            output_path.write_text(tokn, encoding='utf-8')
            self._update_statistics()
            self.status_var.set(f"Saved to {output_path.name}")

    def _toggle_monitoring(self):
        """Toggle file monitoring."""
        if self.monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        """Start monitoring."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first")
            return

        self.monitoring = True
        self._stop_event.clear()
        self.watch_button.configure(text="Stop Watching")

        # Set initial countdown
        try:
            interval = int(self.interval_var.get())
        except ValueError:
            interval = 5
        self._next_check_time = time.time() + interval
        self._update_countdown()

        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring = False
        self._stop_event.set()
        if self._countdown_job:
            self.after_cancel(self._countdown_job)
            self._countdown_job = None
        self.watch_button.configure(text="Start Watching")
        self.status_var.set("Monitoring stopped")

    def _update_countdown(self):
        """Update the countdown display."""
        if not self.monitoring:
            return

        remaining = max(0, self._next_check_time - time.time())
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        self.status_var.set(f"Monitoring: {mins}:{secs:02d}")

        # Schedule next update
        self._countdown_job = self.after(500, self._update_countdown)

    def _monitor_loop(self):
        """Background monitoring loop."""
        mtimes: Dict[Path, float] = {}

        while not self._stop_event.is_set():
            if not self.project_path:
                break

            try:
                changed = False
                for sch_file in self.project_path.glob("**/*.kicad_sch"):
                    try:
                        mtime = sch_file.stat().st_mtime
                        if sch_file in mtimes and mtimes[sch_file] != mtime:
                            changed = True
                        mtimes[sch_file] = mtime
                    except (OSError, IOError):
                        pass

                if changed:
                    self.after(0, self._on_file_changed)

            except Exception:
                pass

            try:
                interval = int(self.interval_var.get())
            except ValueError:
                interval = 5

            # Reset countdown for next check
            self._next_check_time = time.time() + interval

            self._stop_event.wait(interval)

    def _on_file_changed(self):
        """Handle file change."""
        if not self.project_path or not self.monitoring:
            return

        root_sch, _ = find_project_root(self.project_path)
        if root_sch:
            try:
                self.hierarchy = parse_hierarchical_schematic(str(root_sch))
                self.sheet_tree.load_hierarchy(self.hierarchy)

                # Auto-save
                tokn = self._generate_tokn()
                if tokn:
                    output_path = self.project_path / self.output_var.get()
                    output_path.write_text(tokn, encoding='utf-8')
                    self._update_statistics()
                    self.status_var.set(f"Updated: {output_path.name}")
            except Exception as e:
                self.status_var.set(f"Error: {e}")


def main():
    """Main entry point."""
    app = KiCadApp()
    app.mainloop()


if __name__ == "__main__":
    main()

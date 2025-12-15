"""Simplified KiCad Netlist Tool GUI with sheet selection."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import time
from typing import Optional, List, Dict, Tuple

from ..tokn import (
    find_project_root,
    parse_hierarchical_schematic,
    HierarchicalSchematic,
    Schematic,
    encode_sheet_tokn,
    encode_hierarchical_tokn,
)


class SheetTreeView(ttk.Frame):
    """Tree view with checkboxes for selecting schematic sheets."""

    def __init__(self, parent):
        super().__init__(parent)

        # Create treeview with scrollbar
        self.tree = ttk.Treeview(self, selectmode='none', show='tree')
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Track checked items and sheet data
        self.checked: set = set()
        self.sheet_data: Dict[str, Tuple[str, Schematic]] = {}  # item_id -> (hier_path, schematic)

        # Bind click to toggle checkbox
        self.tree.bind('<Button-1>', self._on_click)
        self.tree.bind('<space>', self._on_space)

        # Configure tags for checkbox display
        self.tree.tag_configure('checked', image='')
        self.tree.tag_configure('unchecked', image='')

    def _on_click(self, event):
        """Handle click on tree item."""
        item = self.tree.identify_row(event.y)
        if item:
            self._toggle_item(item)

    def _on_space(self, event):
        """Handle space key on selected item."""
        selection = self.tree.selection()
        if selection:
            self._toggle_item(selection[0])

    def _toggle_item(self, item):
        """Toggle checkbox state for an item."""
        if item in self.checked:
            self.checked.discard(item)
        else:
            self.checked.add(item)
        self._update_display(item)

    def _update_display(self, item):
        """Update the display text to show checkbox state."""
        current_text = self.tree.item(item, 'text')
        # Remove existing checkbox prefix
        if current_text.startswith('[x] ') or current_text.startswith('[ ] '):
            current_text = current_text[4:]

        # Add new checkbox prefix
        prefix = '[x] ' if item in self.checked else '[ ] '
        self.tree.item(item, text=prefix + current_text)

    def clear(self):
        """Clear all items from the tree."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.checked.clear()
        self.sheet_data.clear()

    def load_hierarchy(self, hier: HierarchicalSchematic):
        """Load a hierarchical schematic into the tree."""
        self.clear()

        # Build parent-child relationships from hierarchical paths
        # Paths look like: "project", "project_SheetName", "project_SheetName_SubSheet"
        items_by_path: Dict[str, str] = {}  # hier_path -> tree item id

        for hier_path, schematic in hier.sheets:
            # Determine parent
            parts = hier_path.rsplit('_', 1)
            parent_path = parts[0] if len(parts) > 1 and parts[0] in items_by_path else ''
            parent_item = items_by_path.get(parent_path, '')

            # Get display name
            display_name = schematic.title or schematic.filename or hier_path.split('_')[-1]
            if hier_path == hier.project_name:
                display_name = f"{hier.project_name} (root)"

            # Insert into tree with checkbox prefix
            item_id = self.tree.insert(parent_item, 'end', text=f'[x] {display_name}')
            items_by_path[hier_path] = item_id
            self.sheet_data[item_id] = (hier_path, schematic)
            self.checked.add(item_id)  # Default to checked

        # Expand all items
        for item in self.tree.get_children():
            self._expand_all(item)

    def _expand_all(self, item):
        """Recursively expand all children."""
        self.tree.item(item, open=True)
        for child in self.tree.get_children(item):
            self._expand_all(child)

    def select_all(self):
        """Select all sheets."""
        for item in self.sheet_data.keys():
            self.checked.add(item)
            self._update_display(item)

    def select_none(self):
        """Deselect all sheets."""
        for item in self.sheet_data.keys():
            self.checked.discard(item)
            self._update_display(item)

    def get_selected_sheets(self) -> List[Tuple[str, Schematic]]:
        """Get list of (hier_path, schematic) for checked items."""
        return [self.sheet_data[item] for item in self.checked if item in self.sheet_data]


class KiCadApp:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("KiCad Netlist Tool")
        self.root.geometry("550x500")
        self.root.minsize(450, 400)

        # State
        self.project_path: Optional[Path] = None
        self.hierarchy: Optional[HierarchicalSchematic] = None
        self.monitoring = False
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

        self._setup_ui()
        self._setup_menu()

    def _setup_menu(self):
        """Setup menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Project...", command=self._browse_project)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Options menu
        options_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Options", menu=options_menu)

        self.always_on_top = tk.BooleanVar()
        options_menu.add_checkbutton(
            label="Always on Top",
            variable=self.always_on_top,
            command=self._toggle_always_on_top
        )

        self.include_wires = tk.BooleanVar(value=True)
        options_menu.add_checkbutton(
            label="Include Wire Geometry",
            variable=self.include_wires
        )

    def _setup_ui(self):
        """Setup the main UI."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill='both', expand=True)

        # Project selection section
        project_frame = ttk.LabelFrame(main_frame, text="Project", padding="5")
        project_frame.pack(fill='x', pady=(0, 10))

        # Path entry row
        path_row = ttk.Frame(project_frame)
        path_row.pack(fill='x')

        self.project_var = tk.StringVar()
        self.project_entry = ttk.Entry(path_row, textvariable=self.project_var)
        self.project_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.project_entry.bind('<Return>', lambda e: self._load_project_from_entry())

        ttk.Button(path_row, text="Browse...", command=self._browse_project).pack(side='right')

        # Quick access buttons
        quick_row = ttk.Frame(project_frame)
        quick_row.pack(fill='x', pady=(5, 0))

        ttk.Button(quick_row, text="Examples", command=self._go_examples, width=10).pack(side='left', padx=(0, 5))
        ttk.Button(quick_row, text="Home", command=self._go_home, width=10).pack(side='left', padx=(0, 5))
        ttk.Button(quick_row, text="Current Dir", command=self._go_cwd, width=12).pack(side='left')

        # Sheets section
        sheets_frame = ttk.LabelFrame(main_frame, text="Sheets", padding="5")
        sheets_frame.pack(fill='both', expand=True, pady=(0, 10))

        self.sheet_tree = SheetTreeView(sheets_frame)
        self.sheet_tree.pack(fill='both', expand=True)

        # Selection buttons
        sel_row = ttk.Frame(sheets_frame)
        sel_row.pack(fill='x', pady=(5, 0))

        ttk.Button(sel_row, text="Select All", command=self.sheet_tree.select_all).pack(side='left', padx=(0, 5))
        ttk.Button(sel_row, text="Select None", command=self.sheet_tree.select_none).pack(side='left')

        # Output section
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.pack(fill='x', pady=(0, 10))

        # Filename row
        file_row = ttk.Frame(output_frame)
        file_row.pack(fill='x')

        ttk.Label(file_row, text="Filename:").pack(side='left')
        self.output_var = tk.StringVar(value="netlist.tokn")
        ttk.Entry(file_row, textvariable=self.output_var, width=25).pack(side='left', padx=(5, 0))

        # Action buttons
        btn_row = ttk.Frame(output_frame)
        btn_row.pack(fill='x', pady=(10, 0))

        ttk.Button(btn_row, text="Copy to Clipboard", command=self._copy_to_clipboard).pack(side='left', padx=(0, 10))
        ttk.Button(btn_row, text="Save to File", command=self._save_to_file).pack(side='left')

        # Monitoring section
        monitor_frame = ttk.LabelFrame(main_frame, text="Monitoring", padding="5")
        monitor_frame.pack(fill='x')

        monitor_row = ttk.Frame(monitor_frame)
        monitor_row.pack(fill='x')

        self.watch_button = ttk.Button(monitor_row, text="Start Watching", command=self._toggle_monitoring)
        self.watch_button.pack(side='left', padx=(0, 10))

        ttk.Label(monitor_row, text="Interval:").pack(side='left')
        self.interval_var = tk.StringVar(value="5")
        ttk.Spinbox(monitor_row, from_=1, to=60, width=5, textvariable=self.interval_var).pack(side='left', padx=(5, 0))
        ttk.Label(monitor_row, text="sec").pack(side='left', padx=(2, 0))

        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill='x', pady=(10, 0))

        ttk.Label(status_frame, text="Status:").pack(side='left')
        self.status_var = tk.StringVar(value="Select a project directory")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground='gray')
        self.status_label.pack(side='left', padx=(5, 0))

    def _toggle_always_on_top(self):
        """Toggle always on top."""
        self.root.attributes('-topmost', self.always_on_top.get())

    def _browse_project(self):
        """Open directory browser."""
        initial = str(self.project_path) if self.project_path else str(Path.home())
        directory = filedialog.askdirectory(title="Select KiCad Project Directory", initialdir=initial)
        if directory:
            self._load_project(Path(directory))

    def _load_project_from_entry(self):
        """Load project from the entry field."""
        path_str = self.project_var.get().strip()
        if path_str:
            path = Path(path_str).expanduser().resolve()
            if path.exists() and path.is_dir():
                self._load_project(path)
            else:
                messagebox.showerror("Error", f"Directory not found: {path}")

    def _load_project(self, path: Path):
        """Load a KiCad project from a directory."""
        root_sch, project_name = find_project_root(path)

        if not root_sch:
            messagebox.showwarning("No Project Found", f"No KiCad schematic files found in:\n{path}")
            return

        try:
            self.hierarchy = parse_hierarchical_schematic(str(root_sch))
            self.project_path = path
            self.project_var.set(str(path))

            # Load sheets into tree
            self.sheet_tree.load_hierarchy(self.hierarchy)

            # Update status
            sheet_count = len(self.hierarchy.sheets)
            comp_count = sum(len(s.components) for _, s in self.hierarchy.sheets)
            self.status_var.set(f"Loaded: {project_name} ({sheet_count} sheets, {comp_count} components)")
            self.status_label.config(foreground='green')

        except Exception as e:
            messagebox.showerror("Parse Error", f"Failed to parse schematic:\n{e}")
            self.status_var.set(f"Error: {e}")
            self.status_label.config(foreground='red')

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
        """Navigate to current working directory."""
        self.project_var.set(str(Path.cwd()))
        self._load_project_from_entry()

    def _generate_tokn(self) -> Optional[str]:
        """Generate TOKN output for selected sheets."""
        if not self.hierarchy:
            messagebox.showwarning("No Project", "Please load a project first")
            return None

        selected = self.sheet_tree.get_selected_sheets()
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one sheet")
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
        """Copy TOKN output to clipboard."""
        tokn = self._generate_tokn()
        if tokn:
            self.root.clipboard_clear()
            self.root.clipboard_append(tokn)

            selected = self.sheet_tree.get_selected_sheets()
            self.status_var.set(f"Copied {len(selected)} sheet(s) to clipboard")
            self.status_label.config(foreground='blue')

    def _save_to_file(self):
        """Save TOKN output to file."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first")
            return

        tokn = self._generate_tokn()
        if tokn:
            output_path = self.project_path / self.output_var.get()
            output_path.write_text(tokn, encoding='utf-8')

            self.status_var.set(f"Saved to {output_path.name}")
            self.status_label.config(foreground='green')

    def _toggle_monitoring(self):
        """Toggle file monitoring."""
        if self.monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        """Start monitoring for file changes."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first")
            return

        self.monitoring = True
        self._stop_event.clear()
        self.watch_button.config(text="Stop Watching")
        self.status_var.set("Monitoring for changes...")
        self.status_label.config(foreground='orange')

        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _stop_monitoring(self):
        """Stop monitoring for file changes."""
        self.monitoring = False
        self._stop_event.set()
        self.watch_button.config(text="Start Watching")
        self.status_var.set("Monitoring stopped")
        self.status_label.config(foreground='gray')

    def _monitor_loop(self):
        """Background thread for monitoring file changes."""
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
                    self.root.after(0, self._on_file_changed)

            except Exception:
                pass

            try:
                interval = int(self.interval_var.get())
            except ValueError:
                interval = 5

            self._stop_event.wait(interval)

    def _on_file_changed(self):
        """Handle file change detection."""
        if not self.project_path or not self.monitoring:
            return

        # Reload project
        root_sch, _ = find_project_root(self.project_path)
        if root_sch:
            try:
                self.hierarchy = parse_hierarchical_schematic(str(root_sch))
                self.sheet_tree.load_hierarchy(self.hierarchy)

                # Auto-regenerate output
                tokn = self._generate_tokn()
                if tokn:
                    output_path = self.project_path / self.output_var.get()
                    output_path.write_text(tokn, encoding='utf-8')
                    self.status_var.set(f"Updated: {output_path.name}")
                    self.status_label.config(foreground='green')
            except Exception as e:
                self.status_var.set(f"Error: {e}")
                self.status_label.config(foreground='red')

    def run(self):
        """Run the application."""
        try:
            self.root.mainloop()
        finally:
            self._stop_event.set()


def main():
    """Main entry point."""
    app = KiCadApp()
    app.run()


if __name__ == "__main__":
    main()

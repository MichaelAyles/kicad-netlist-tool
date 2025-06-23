"""Main GUI window for KiCad Netlist Tool."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
import json

from ..parser import KiCadSchematicParser
from ..formatter import CompactFormatter
from ..watcher import SchematicWatcher
from ..tokenizer import SimpleTokenizer, TokenStats


class ChangelogManager:
    """Manages changelog generation for netlist updates."""
    
    def __init__(self, changelog_path: Path):
        self.changelog_path = changelog_path
        self.last_state: Optional[Dict[str, Any]] = None
        
    def record_change(self, components: Dict, nets: Dict, reason: str = "File changed"):
        """Record a change in the changelog."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create current state summary
        current_state = {
            "component_count": len(components),
            "net_count": len(nets),
            "components": {ref: {"value": comp.value, "footprint": comp.footprint} 
                         for ref, comp in components.items()},
            "nets": {name: list(net.connections) if hasattr(net, 'connections') else []
                    for name, net in nets.items()}
        }
        
        # Compare with last state
        changes = []
        if self.last_state:
            # Check for component changes
            for ref, comp_data in current_state["components"].items():
                if ref not in self.last_state["components"]:
                    changes.append(f"  + Added component {ref}: {comp_data['value']}")
                elif comp_data != self.last_state["components"][ref]:
                    changes.append(f"  * Modified component {ref}: {comp_data['value']}")
            
            # Check for removed components
            for ref in self.last_state["components"]:
                if ref not in current_state["components"]:
                    changes.append(f"  - Removed component {ref}")
            
            # Check for net changes
            for net_name, connections in current_state["nets"].items():
                if net_name not in self.last_state["nets"]:
                    changes.append(f"  + Added net {net_name} ({len(connections)} connections)")
                elif set(map(tuple, connections)) != set(map(tuple, self.last_state["nets"][net_name])):
                    changes.append(f"  * Modified net {net_name} ({len(connections)} connections)")
            
            # Check for removed nets
            for net_name in self.last_state["nets"]:
                if net_name not in current_state["nets"]:
                    changes.append(f"  - Removed net {net_name}")
        else:
            changes.append(f"  + Initial netlist generation")
            changes.append(f"    - {len(components)} components")
            changes.append(f"    - {len(nets)} nets")
        
        # Write to changelog
        with open(self.changelog_path, 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}] {reason}\n")
            if changes:
                for change in changes:
                    f.write(f"{change}\n")
            else:
                f.write("  No changes detected\n")
        
        self.last_state = current_state


class KiCadNetlistGUI:
    """Main GUI application for KiCad Netlist Tool."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("KiCad Netlist Tool")
        self.root.geometry("750x650")
        
        # State variables
        self.watching = False
        self.watcher_thread: Optional[threading.Thread] = None
        self.project_path: Optional[Path] = None
        self.output_path: Optional[Path] = None
        self.changelog_path: Optional[Path] = None
        self.changelog_manager: Optional[ChangelogManager] = None
        self.stop_watching = threading.Event()
        self.token_stats = TokenStats()
        
        self.setup_ui()
        self.setup_menu()
        
    def setup_menu(self):
        """Setup the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Project Directory...", command=self.select_project)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Options menu
        options_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Options", menu=options_menu)
        
        self.always_on_top = tk.BooleanVar()
        options_menu.add_checkbutton(label="Always on Top", variable=self.always_on_top,
                                   command=self.toggle_always_on_top)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
    def setup_ui(self):
        """Setup the main UI."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(8, weight=1)
        
        # Project selection
        ttk.Label(main_frame, text="KiCad Project:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Project path frame with entry and browse button
        project_frame = ttk.Frame(main_frame)
        project_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(10, 0))
        project_frame.columnconfigure(0, weight=1)
        
        self.project_var = tk.StringVar(value="")
        self.project_entry = ttk.Entry(project_frame, textvariable=self.project_var, width=50)
        self.project_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.project_entry.bind('<Return>', lambda e: self.validate_project_path())
        
        ttk.Button(project_frame, text="Browse...", 
                  command=self.select_project).grid(row=0, column=1)
        
        # Quick access buttons
        quick_frame = ttk.Frame(main_frame)
        quick_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(2, 5))
        
        ttk.Button(quick_frame, text="Examples", command=self.go_to_examples, 
                  width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="Home", command=self.go_to_home, 
                  width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="Current Dir", command=self.go_to_current_dir, 
                  width=12).pack(side=tk.LEFT)
        
        # Output file
        ttk.Label(main_frame, text="Output File:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar(value="netlist_summary.txt")
        ttk.Entry(main_frame, textvariable=self.output_var).grid(row=2, column=1, 
                                                               sticky=(tk.W, tk.E), padx=(10, 0))
        
        # Status
        ttk.Label(main_frame, text="Status:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                     foreground="green")
        self.status_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Watching", 
                                      command=self.toggle_watching)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Generate Once", 
                  command=self.generate_once).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Open Output", 
                  command=self.open_output).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="View Changelog", 
                  command=self.view_changelog).pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=5, column=0, columnspan=3, 
                                                           sticky=(tk.W, tk.E), pady=10)
        
        # Statistics Panel
        self.setup_statistics_panel(main_frame, row=6)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="5")
        settings_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        settings_frame.columnconfigure(1, weight=1)
        
        ttk.Label(settings_frame, text="Update Interval:").grid(row=0, column=0, sticky=tk.W)
        self.interval_var = tk.StringVar(value="30")
        interval_spin = ttk.Spinbox(settings_frame, from_=5, to=300, width=10, 
                                   textvariable=self.interval_var)
        interval_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Label(settings_frame, text="seconds").grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=50)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initial log message
        self.log("KiCad Netlist Tool started")
        
    def setup_statistics_panel(self, parent, row):
        """Setup the statistics display panel."""
        stats_frame = ttk.LabelFrame(parent, text="📊 Token Reduction Statistics", padding="8")
        stats_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        # Create main stats display
        main_stats_frame = ttk.Frame(stats_frame)
        main_stats_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        main_stats_frame.columnconfigure(0, weight=1)
        main_stats_frame.columnconfigure(1, weight=1)
        main_stats_frame.columnconfigure(2, weight=1)
        
        # Before column
        before_frame = ttk.Frame(main_stats_frame, relief="ridge", borderwidth=1)
        before_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 2))
        before_frame.columnconfigure(0, weight=1)
        
        ttk.Label(before_frame, text="📄 BEFORE", font=("TkDefaultFont", 9, "bold"),
                 foreground="#d32f2f").pack(pady=(5, 2))
        
        self.before_tokens_var = tk.StringVar(value="0")
        self.before_size_var = tk.StringVar(value="0 B")
        self.before_files_var = tk.StringVar(value="0 files")
        
        ttk.Label(before_frame, textvariable=self.before_tokens_var, 
                 font=("TkDefaultFont", 11, "bold")).pack()
        ttk.Label(before_frame, text="tokens", foreground="gray").pack()
        ttk.Label(before_frame, textvariable=self.before_size_var, 
                 font=("TkDefaultFont", 9)).pack(pady=(2, 0))
        ttk.Label(before_frame, textvariable=self.before_files_var,
                 font=("TkDefaultFont", 8), foreground="gray").pack(pady=(0, 5))
        
        # Arrow column
        arrow_frame = ttk.Frame(main_stats_frame)
        arrow_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        ttk.Label(arrow_frame, text="➜", font=("TkDefaultFont", 16, "bold"),
                 foreground="#1976d2").pack(expand=True)
        
        # After column  
        after_frame = ttk.Frame(main_stats_frame, relief="ridge", borderwidth=1)
        after_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(2, 0))
        after_frame.columnconfigure(0, weight=1)
        
        ttk.Label(after_frame, text="📝 AFTER", font=("TkDefaultFont", 9, "bold"),
                 foreground="#388e3c").pack(pady=(5, 2))
        
        self.after_tokens_var = tk.StringVar(value="0")
        self.after_size_var = tk.StringVar(value="0 B")
        
        ttk.Label(after_frame, textvariable=self.after_tokens_var,
                 font=("TkDefaultFont", 11, "bold")).pack()
        ttk.Label(after_frame, text="tokens", foreground="gray").pack()
        ttk.Label(after_frame, textvariable=self.after_size_var,
                 font=("TkDefaultFont", 9)).pack(pady=(2, 0))
        ttk.Label(after_frame, text="1 summary file",
                 font=("TkDefaultFont", 8), foreground="gray").pack(pady=(0, 5))
        
        # Reduction display
        reduction_frame = ttk.Frame(stats_frame)
        reduction_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        reduction_frame.columnconfigure(0, weight=1)
        
        # Token reduction
        token_reduction_frame = ttk.Frame(reduction_frame, relief="solid", borderwidth=1)
        token_reduction_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        ttk.Label(token_reduction_frame, text="🎯 Token Reduction", 
                 font=("TkDefaultFont", 9, "bold")).pack(pady=(3, 1))
        
        self.token_reduction_var = tk.StringVar(value="0.0%")
        ttk.Label(token_reduction_frame, textvariable=self.token_reduction_var,
                 font=("TkDefaultFont", 14, "bold"), foreground="#e65100").pack()
        
        self.token_savings_var = tk.StringVar(value="(0 tokens saved)")
        ttk.Label(token_reduction_frame, textvariable=self.token_savings_var,
                 font=("TkDefaultFont", 8), foreground="gray").pack(pady=(0, 3))
        
        # Size reduction
        size_reduction_frame = ttk.Frame(reduction_frame, relief="solid", borderwidth=1)
        size_reduction_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))
        
        ttk.Label(size_reduction_frame, text="💾 Size Reduction",
                 font=("TkDefaultFont", 9, "bold")).pack(pady=(3, 1))
        
        self.size_reduction_var = tk.StringVar(value="0.0%")
        ttk.Label(size_reduction_frame, textvariable=self.size_reduction_var,
                 font=("TkDefaultFont", 14, "bold"), foreground="#7b1fa2").pack()
        
        self.size_savings_var = tk.StringVar(value="(0 B saved)")
        ttk.Label(size_reduction_frame, textvariable=self.size_savings_var,
                 font=("TkDefaultFont", 8), foreground="gray").pack(pady=(0, 3))
        
        # Circuit info
        circuit_frame = ttk.Frame(stats_frame)
        circuit_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.circuit_info_var = tk.StringVar(value="No circuit loaded")
        ttk.Label(circuit_frame, textvariable=self.circuit_info_var,
                 font=("TkDefaultFont", 8), foreground="#555").pack()
        
    def log(self, message: str):
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def update_statistics_display(self):
        """Update the statistics display with current token stats."""
        # Update before stats
        self.before_tokens_var.set(SimpleTokenizer.format_number(self.token_stats.original_tokens))
        self.before_size_var.set(self.format_file_size(self.token_stats.original_size))
        file_text = "file" if self.token_stats.file_count == 1 else "files"
        self.before_files_var.set(f"{self.token_stats.file_count} {file_text}")
        
        # Update after stats
        self.after_tokens_var.set(SimpleTokenizer.format_number(self.token_stats.compressed_tokens))
        self.after_size_var.set(self.format_file_size(self.token_stats.compressed_size))
        
        # Update reductions
        token_reduction = self.token_stats.token_reduction
        self.token_reduction_var.set(SimpleTokenizer.format_reduction(token_reduction))
        
        token_savings = self.token_stats.original_tokens - self.token_stats.compressed_tokens
        self.token_savings_var.set(f"({SimpleTokenizer.format_number(token_savings)} tokens saved)")
        
        size_reduction = self.token_stats.size_reduction
        self.size_reduction_var.set(SimpleTokenizer.format_reduction(size_reduction))
        
        size_savings = self.token_stats.original_size - self.token_stats.compressed_size
        self.size_savings_var.set(f"({self.format_file_size(size_savings)} saved)")
        
        # Update circuit info
        if self.token_stats.component_count > 0:
            info = (f"Circuit: {self.token_stats.component_count} components, "
                   f"{self.token_stats.net_count} nets, "
                   f"{self.token_stats.connection_count} connections")
            self.circuit_info_var.set(info)
        else:
            self.circuit_info_var.set("No circuit loaded")
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                if unit == 'B':
                    return f"{size_bytes} {unit}"
                else:
                    return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
        
    def select_project(self):
        """Select KiCad project directory."""
        initial_dir = str(self.project_path) if self.project_path else str(Path.home())
        directory = filedialog.askdirectory(title="Select KiCad Project Directory", 
                                          initialdir=initial_dir)
        if directory:
            self.set_project_path(Path(directory))
            
    def validate_project_path(self):
        """Validate and set the project path from the entry field."""
        path_str = self.project_var.get().strip()
        if path_str:
            path = Path(path_str).expanduser().resolve()
            if path.exists() and path.is_dir():
                self.set_project_path(path)
            else:
                messagebox.showerror("Error", f"Directory does not exist: {path}")
                
    def set_project_path(self, path: Path):
        """Set the project path and update UI."""
        self.project_path = path
        self.project_var.set(str(self.project_path))
        
        # Auto-set output paths
        self.output_path = self.project_path / self.output_var.get()
        self.changelog_path = self.project_path / "netlist_changelog.txt"
        self.changelog_manager = ChangelogManager(self.changelog_path)
        
        self.log(f"Selected project: {self.project_path}")
        
        # Check for .kicad_sch files
        sch_files = list(self.project_path.glob("*.kicad_sch"))
        self.log(f"Found {len(sch_files)} schematic files")
        
    def go_to_examples(self):
        """Navigate to the examples directory."""
        # Find the package directory
        import kicad_netlist_tool
        package_dir = Path(kicad_netlist_tool.__file__).parent.parent
        examples_dir = package_dir / "examples"
        
        if examples_dir.exists():
            self.set_project_path(examples_dir)
        else:
            messagebox.showwarning("Warning", "Examples directory not found")
            
    def go_to_home(self):
        """Navigate to the user's home directory."""
        self.set_project_path(Path.home())
        
    def go_to_current_dir(self):
        """Navigate to the current working directory."""
        self.set_project_path(Path.cwd())
            
    def toggle_watching(self):
        """Start or stop watching for file changes."""
        if not self.project_path:
            messagebox.showerror("Error", "Please select a project directory first")
            return
            
        if not self.watching:
            self.start_watching()
        else:
            self.stop_watching_files()
            
    def start_watching(self):
        """Start watching for file changes."""
        self.watching = True
        self.stop_watching.clear()
        self.start_button.config(text="Stop Watching")
        self.status_var.set("Watching for changes...")
        self.status_label.config(foreground="orange")
        
        # Start watcher thread
        self.watcher_thread = threading.Thread(target=self.watch_files, daemon=True)
        self.watcher_thread.start()
        
        self.log("Started watching for schematic changes")
        
    def stop_watching_files(self):
        """Stop watching for file changes."""
        self.watching = False
        self.stop_watching.set()
        self.start_button.config(text="Start Watching")
        self.status_var.set("Ready")
        self.status_label.config(foreground="green")
        
        self.log("Stopped watching")
        
    def watch_files(self):
        """File watching loop."""
        interval = int(self.interval_var.get())
        last_check = {}
        
        while not self.stop_watching.is_set():
            try:
                sch_files = list(self.project_path.glob("*.kicad_sch"))
                files_changed = False
                
                for sch_file in sch_files:
                    mtime = sch_file.stat().st_mtime
                    if sch_file not in last_check or last_check[sch_file] != mtime:
                        last_check[sch_file] = mtime
                        files_changed = True
                        self.log(f"Detected change in {sch_file.name}")
                
                if files_changed:
                    self.generate_netlist("Schematic file changed")
                    
            except Exception as e:
                self.log(f"Error during file watching: {e}")
                
            # Wait for interval or stop signal
            self.stop_watching.wait(interval)
            
    def generate_once(self):
        """Generate netlist once."""
        if not self.project_path:
            messagebox.showerror("Error", "Please select a project directory first")
            return
            
        self.generate_netlist("Manual generation")
        
    def generate_netlist(self, reason: str = "Generated"):
        """Generate the netlist summary."""
        try:
            # Find schematic files
            sch_files = list(self.project_path.glob("*.kicad_sch"))
            if not sch_files:
                self.log("No .kicad_sch files found in project directory")
                return
                
            self.log(f"Processing {len(sch_files)} schematic file(s)...")
            
            # Parse all files
            parser = KiCadSchematicParser()
            all_components = {}
            all_nets = {}
            
            for sch_file in sch_files:
                components, nets = parser.parse_file(sch_file)
                all_components.update(components)
                all_nets.update(nets)
                
            # Generate output
            output_path = self.project_path / self.output_var.get()
            with open(output_path, 'w') as f:
                CompactFormatter.write(all_components, all_nets, f)
                
            # Calculate token statistics
            self.token_stats.update_from_files(sch_files, output_path, all_components, all_nets)
            self.update_statistics_display()
            
            # Update changelog
            if self.changelog_manager:
                self.changelog_manager.record_change(all_components, all_nets, reason)
            
            # Log results with token info
            token_reduction = self.token_stats.token_reduction
            self.log(f"Generated netlist: {len(all_components)} components, {len(all_nets)} nets")
            self.log(f"Token reduction: {SimpleTokenizer.format_reduction(token_reduction)} "
                    f"({SimpleTokenizer.format_number(self.token_stats.original_tokens)} → "
                    f"{SimpleTokenizer.format_number(self.token_stats.compressed_tokens)})")
            
        except Exception as e:
            self.log(f"Error generating netlist: {e}")
            messagebox.showerror("Error", f"Failed to generate netlist: {e}")
            
    def open_output(self):
        """Open the output file."""
        if self.project_path:
            output_path = self.project_path / self.output_var.get()
            if output_path.exists():
                import subprocess
                import sys
                
                if sys.platform == "win32":
                    subprocess.run(["notepad", str(output_path)])
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(output_path)])
                else:
                    subprocess.run(["xdg-open", str(output_path)])
            else:
                messagebox.showwarning("Warning", "Output file does not exist yet")
        else:
            messagebox.showerror("Error", "No project selected")
            
    def view_changelog(self):
        """View the changelog."""
        if self.changelog_path and self.changelog_path.exists():
            # Open changelog in a new window
            changelog_window = tk.Toplevel(self.root)
            changelog_window.title("Netlist Changelog")
            changelog_window.geometry("600x400")
            
            text_widget = scrolledtext.ScrolledText(changelog_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            with open(self.changelog_path, 'r') as f:
                text_widget.insert(tk.END, f.read())
                
            text_widget.config(state=tk.DISABLED)
        else:
            messagebox.showwarning("Warning", "No changelog available yet")
            
    def toggle_always_on_top(self):
        """Toggle always on top setting."""
        self.root.attributes('-topmost', self.always_on_top.get())
        
    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo("About", 
                          "🔧 KiCad Netlist Tool v1.0\n\n"
                          "📊 Real-time token reduction statistics\n"
                          "🔄 Automatic file watching & updates\n"
                          "📝 Changelog tracking\n"
                          "📄 Multiple export formats\n\n"
                          "Extracts component and netlist information\n"
                          "from KiCad schematic files in a token-efficient\n"
                          "format for LLM documentation.\n\n"
                          "✨ Achieves 96%+ token reduction while preserving\n"
                          "complete circuit connectivity information!")
        
    def run(self):
        """Run the GUI application."""
        try:
            self.root.mainloop()
        finally:
            if self.watching:
                self.stop_watching_files()


def main():
    """Main entry point for GUI application."""
    app = KiCadNetlistGUI()
    app.run()


if __name__ == "__main__":
    main()
"""File watcher for automatic netlist updates."""

import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .parser import parse_schematic, analyze_connectivity
from .formatter import ToknFormatter, CompactFormatter, MarkdownFormatter, JsonFormatter


class SchematicHandler(FileSystemEventHandler):
    """Handles file system events for KiCad schematic files."""

    def __init__(self, project_path: Path, output_path: Path,
                 format: str = 'tokn', update_interval: int = 30):
        self.project_path = project_path
        self.output_path = output_path
        self.format = format
        self.update_interval = update_interval
        self.last_update = 0

        # Do initial parse
        self.update_netlist()

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check if it's a schematic file
        path = Path(event.src_path)
        if path.suffix == '.kicad_sch':
            current_time = time.time()
            if current_time - self.last_update >= self.update_interval:
                print(f"Detected change in {path.name}, updating netlist...")
                self.update_netlist()
                self.last_update = current_time

    def update_netlist(self):
        """Update the netlist file."""
        # Find all schematic files
        if self.project_path.is_file():
            schematic_files = [self.project_path]
        else:
            schematic_files = list(self.project_path.glob('*.kicad_sch'))

        if not schematic_files:
            return

        try:
            if self.format == 'tokn':
                # For TOKN, use the first file
                sch = parse_schematic(str(schematic_files[0]))
                netlist = analyze_connectivity(sch)

                with open(self.output_path, 'w', encoding='utf-8') as f:
                    ToknFormatter.write(sch, netlist, f)
            else:
                # For other formats, merge all files
                all_components = []
                all_nets = []

                for sch_file in schematic_files:
                    sch = parse_schematic(str(sch_file))
                    netlist = analyze_connectivity(sch)
                    all_components.extend(netlist.components)
                    all_nets.extend(netlist.nets)

                with open(self.output_path, 'w', encoding='utf-8') as f:
                    if self.format == 'compact':
                        CompactFormatter.write(all_components, all_nets, f)
                    elif self.format == 'markdown':
                        MarkdownFormatter.write(all_components, all_nets, f)
                    elif self.format == 'json':
                        JsonFormatter.write(all_components, all_nets, f)

            print(f"Updated {self.output_path}")

        except Exception as e:
            print(f"Error updating netlist: {e}")


class SchematicWatcher:
    """Watches KiCad project for schematic changes."""

    def __init__(self, project_path: Path, output_path: Path,
                 format: str = 'tokn', update_interval: int = 30):
        self.project_path = project_path
        self.output_path = output_path
        self.format = format
        self.update_interval = update_interval

    def run(self):
        """Start watching for changes."""
        handler = SchematicHandler(
            self.project_path,
            self.output_path,
            self.format,
            self.update_interval
        )

        observer = Observer()
        watch_path = self.project_path if self.project_path.is_dir() else self.project_path.parent
        observer.schedule(handler, str(watch_path), recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()

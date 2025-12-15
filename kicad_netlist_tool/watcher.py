"""File watcher for automatic netlist updates."""

import time
from pathlib import Path
from typing import Type
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from .parser import KiCadSchematicParser
from .formatter import CompactFormatter


class SchematicHandler(FileSystemEventHandler):
    """Handles file system events for KiCad schematic files."""
    
    def __init__(self, project_path: Path, output_path: Path, 
                 formatter: Type, update_interval: int = 30):
        self.project_path = project_path
        self.output_path = output_path
        self.formatter = formatter
        self.update_interval = update_interval
        self.last_update = 0
        self.parser = KiCadSchematicParser()
        
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
        
        # Parse all files
        all_components = {}
        all_nets = {}
        
        for sch_file in schematic_files:
            try:
                components, nets = self.parser.parse_file(sch_file)
                all_components.update(components)
                all_nets.update(nets)
            except Exception as e:
                print(f"Error parsing {sch_file}: {e}")
                continue
        
        # Write output
        try:
            with open(self.output_path, 'w') as f:
                self.formatter.write(all_components, all_nets, f)
            print(f"Updated {self.output_path}")
        except Exception as e:
            print(f"Error writing output: {e}")


class SchematicWatcher:
    """Watches KiCad project for schematic changes."""
    
    def __init__(self, project_path: Path, output_path: Path,
                 formatter: Type = CompactFormatter, update_interval: int = 30):
        self.project_path = project_path
        self.output_path = output_path
        self.formatter = formatter
        self.update_interval = update_interval
    
    def run(self):
        """Start watching for changes."""
        handler = SchematicHandler(
            self.project_path, 
            self.output_path,
            self.formatter,
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
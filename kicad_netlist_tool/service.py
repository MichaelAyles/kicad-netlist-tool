"""Core NetlistService for centralized netlist processing and file monitoring."""

import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List

from datetime import datetime

from .parser import parse_schematic, analyze_connectivity, Netlist
from .tokn import parse_hierarchical_schematic, find_project_root, HierarchicalSchematic
from .formatter import ToknFormatter
from .tokenizer import SimpleTokenizer, TokenStats
from .shared_state import get_shared_state


class NetlistService:
    """Core service that handles all netlist processing and file monitoring."""

    def __init__(self):
        self.shared_state = get_shared_state()
        self.tokenizer = SimpleTokenizer()

        # Service state
        self._running = False
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()

        # Callbacks for status updates
        self._status_callbacks: List[Callable[[str], None]] = []
        self._log_callbacks: List[Callable[[str], None]] = []

        # Current processing state
        self.last_check: Dict[Path, float] = {}
        self.last_generation_state: Optional[Dict[str, Any]] = None

    def add_status_callback(self, callback: Callable[[str], None]):
        """Add a callback for status updates."""
        self._status_callbacks.append(callback)

    def add_log_callback(self, callback: Callable[[str], None]):
        """Add a callback for log messages."""
        self._log_callbacks.append(callback)

    def remove_status_callback(self, callback: Callable[[str], None]):
        """Remove a status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def remove_log_callback(self, callback: Callable[[str], None]):
        """Remove a log callback."""
        if callback in self._log_callbacks:
            self._log_callbacks.remove(callback)

    def _notify_status(self, status: str):
        """Notify all status callbacks."""
        for callback in self._status_callbacks:
            try:
                callback(status)
            except Exception:
                pass  # Don't let callback errors crash the service

    def _notify_log(self, message: str):
        """Notify all log callbacks."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        for callback in self._log_callbacks:
            try:
                callback(log_message)
            except Exception:
                pass  # Don't let callback errors crash the service

    def start(self):
        """Start the service."""
        if self._running:
            return

        self._running = True
        self._notify_status("Service started")
        self._notify_log("NetlistService started")

        # Load state and potentially start monitoring
        state = self.shared_state.get_state()
        if state.monitoring and state.project_path:
            self.start_monitoring(Path(state.project_path))

    def stop(self):
        """Stop the service."""
        if not self._running:
            return

        self.stop_monitoring()
        self._running = False
        self._notify_status("Service stopped")
        self._notify_log("NetlistService stopped")

    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running

    def is_monitoring(self) -> bool:
        """Check if file monitoring is active."""
        return self._monitoring

    def set_project_path(self, path: Path) -> bool:
        """Set the project path and validate it."""
        if not path.exists() or not path.is_dir():
            self._notify_log(f"Invalid project path: {path}")
            return False

        # Check for .kicad_sch files
        sch_files = list(path.glob("*.kicad_sch"))
        if not sch_files:
            self._notify_log(f"No .kicad_sch files found in {path}")
            return False

        # Update shared state
        self.shared_state.update_project_path(path)
        self._notify_log(f"Project path set to: {path}")
        self._notify_log(f"Found {len(sch_files)} schematic file(s)")

        return True

    def get_project_path(self) -> Optional[Path]:
        """Get the current project path."""
        return self.shared_state.get_project_path()

    def set_output_file(self, filename: str):
        """Set the output filename."""
        self.shared_state.update_output_file(filename)
        self._notify_log(f"Output file set to: {filename}")

    def set_update_interval(self, interval: int):
        """Set the monitoring update interval."""
        self.shared_state.update_interval(interval)
        self._notify_log(f"Update interval set to: {interval} seconds")

    def generate_netlist(self, reason: str = "Manual generation") -> bool:
        """Generate netlist for current project."""
        project_path = self.get_project_path()
        if not project_path:
            self._notify_log("No project path set")
            return False

        state = self.shared_state.get_state()

        try:
            # Find root schematic from project file or directory
            root_sch_path, project_name = find_project_root(project_path)

            if not root_sch_path:
                # Fallback: find any .kicad_sch files
                sch_files = list(project_path.glob("*.kicad_sch"))
                if not sch_files:
                    self._notify_log("No .kicad_sch files found")
                    return False
                root_sch_path = sch_files[0]
                project_name = root_sch_path.stem

            self._notify_status("Generating netlist...")
            self._notify_log(f"Project: {project_name}")
            self._notify_log(f"Root schematic: {root_sch_path.name}")

            # Parse hierarchically to get all sheets
            hier = parse_hierarchical_schematic(str(root_sch_path))

            self._notify_log(f"Found {len(hier.sheets)} sheet(s)")
            for path, sch in hier.sheets:
                self._notify_log(f"  {path}: {len(sch.components)} components")

            # Generate hierarchical TOKN output
            output_path = project_path / state.output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                ToknFormatter.write_hierarchical(hier, f)

            # Calculate token statistics
            token_stats = TokenStats()
            token_stats.file_count = len(hier.sheets)

            # Calculate original tokens from all sheet files
            for _, sch in hier.sheets:
                if sch.filename:
                    sch_file = project_path / sch.filename
                    if sch_file.exists():
                        token_stats.original_tokens += SimpleTokenizer.count_file_tokens(sch_file)
                        token_stats.original_size += SimpleTokenizer.get_file_size(sch_file)

            # Calculate compressed tokens
            token_stats.compressed_tokens = SimpleTokenizer.count_file_tokens(output_path)
            token_stats.compressed_size = SimpleTokenizer.get_file_size(output_path)

            # Circuit stats - count from all sheets
            all_components = hier.all_components
            token_stats.component_count = len(all_components)
            token_stats.net_count = len(hier.sheets)  # Approximate - sheets as "nets"
            token_stats.connection_count = 0  # Not tracking connections in hierarchical mode

            # Check for changes compared to last generation
            current_state = {
                "component_count": len(all_components),
                "sheet_count": len(hier.sheets),
                "components": {c.reference: {"value": c.value, "footprint": c.footprint}
                             for c in all_components},
                "sheets": [(path, len(sch.components)) for path, sch in hier.sheets]
            }

            # Determine if this is initial generation or has changes
            is_initial = self.last_generation_state is None
            has_changes = True

            if not is_initial:
                # Check if anything actually changed
                has_changes = (
                    current_state["component_count"] != self.last_generation_state.get("component_count") or
                    current_state["sheet_count"] != self.last_generation_state.get("sheet_count") or
                    current_state["components"] != self.last_generation_state.get("components") or
                    current_state["sheets"] != self.last_generation_state.get("sheets")
                )

            # Update shared state with statistics
            self.shared_state.update_stats(
                token_stats,
                len(all_components),
                len(hier.sheets),
                token_stats.connection_count
            )

            # Log success with appropriate message
            self._notify_status("Ready")

            if is_initial:
                self._notify_log(f"Initial generation: {len(all_components)} components across {len(hier.sheets)} sheets")
            elif not has_changes:
                self._notify_log(f"Regenerated, no changes: {len(all_components)} components, {len(hier.sheets)} sheets")
            else:
                # Log detailed changes
                self._log_hierarchical_changes(current_state, self.last_generation_state)
                self._notify_log(f"Updated: {len(all_components)} components across {len(hier.sheets)} sheets")

            self._notify_log(f"Token reduction: {SimpleTokenizer.format_reduction(token_stats.token_reduction)} "
                           f"({SimpleTokenizer.format_number(token_stats.original_tokens)} → "
                           f"{SimpleTokenizer.format_number(token_stats.compressed_tokens)})")

            # Update changelog if there's a change or it's initial
            if has_changes or is_initial:
                self._update_hierarchical_changelog(project_path, hier, current_state, reason, is_initial)

            # Store current state for next comparison
            self.last_generation_state = current_state

            return True

        except Exception as e:
            self._notify_status("Error")
            self._notify_log(f"Error generating netlist: {e}")
            return False

    def start_monitoring(self, project_path: Optional[Path] = None) -> bool:
        """Start file monitoring."""
        if self._monitoring:
            return True

        if project_path:
            if not self.set_project_path(project_path):
                return False
        else:
            project_path = self.get_project_path()

        if not project_path:
            self._notify_log("No project path available for monitoring")
            return False

        self._monitoring = True
        self._stop_monitoring.clear()
        self.shared_state.update_monitoring(True)

        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_files, daemon=True)
        self._monitor_thread.start()

        self._notify_status("Monitoring for changes...")
        self._notify_log("Started file monitoring")

        return True

    def stop_monitoring(self):
        """Stop file monitoring."""
        if not self._monitoring:
            return

        self._monitoring = False
        self._stop_monitoring.set()
        self.shared_state.update_monitoring(False)

        # Wait for thread to finish
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)

        self._notify_status("Ready")
        self._notify_log("Stopped file monitoring")

    def _monitor_files(self):
        """File monitoring loop."""
        state = self.shared_state.get_state()
        interval = state.update_interval
        project_path = self.get_project_path()

        if not project_path:
            return

        while not self._stop_monitoring.is_set():
            try:
                sch_files = list(project_path.glob("*.kicad_sch"))
                files_changed = False

                for sch_file in sch_files:
                    mtime = sch_file.stat().st_mtime
                    if sch_file not in self.last_check or self.last_check[sch_file] != mtime:
                        self.last_check[sch_file] = mtime
                        files_changed = True
                        self._notify_log(f"Detected change in {sch_file.name}")

                if files_changed:
                    self.generate_netlist("Schematic file changed")

            except Exception as e:
                self._notify_log(f"Error during file monitoring: {e}")

            # Wait for interval or stop signal
            self._stop_monitoring.wait(interval)

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of current service status."""
        state = self.shared_state.get_state()
        project_path = self.get_project_path()

        summary = {
            "running": self._running,
            "monitoring": self._monitoring,
            "project_path": str(project_path) if project_path else None,
            "output_file": state.output_file,
            "update_interval": state.update_interval,
            "last_update": state.last_update,
            "statistics": state.token_stats,
            "component_count": state.component_count,
            "net_count": state.net_count,
            "connection_count": state.connection_count
        }

        if project_path:
            sch_files = list(project_path.glob("*.kicad_sch"))
            summary["schematic_files"] = len(sch_files)
        else:
            summary["schematic_files"] = 0

        return summary

    def _log_hierarchical_changes(self, current_state: Dict[str, Any], last_state: Dict[str, Any]):
        """Log detailed changes between hierarchical states."""
        # Check for component changes
        current_components = current_state.get("components", {})
        last_components = last_state.get("components", {})

        for ref, comp_data in current_components.items():
            if ref not in last_components:
                self._notify_log(f"Added component {ref}: {comp_data['value']}")
            elif comp_data != last_components[ref]:
                old_value = last_components[ref]['value']
                new_value = comp_data['value']
                if old_value != new_value:
                    self._notify_log(f"Modified component {ref}: {old_value} → {new_value}")
                else:
                    self._notify_log(f"Modified component {ref} footprint")

        for ref in last_components:
            if ref not in current_components:
                self._notify_log(f"Removed component {ref}")

        # Check for sheet changes
        current_sheets = dict(current_state.get("sheets", []))
        last_sheets = dict(last_state.get("sheets", []))

        for sheet_name, comp_count in current_sheets.items():
            if sheet_name not in last_sheets:
                self._notify_log(f"Added sheet {sheet_name} ({comp_count} components)")
            elif comp_count != last_sheets[sheet_name]:
                self._notify_log(f"Modified sheet {sheet_name}: {last_sheets[sheet_name]} → {comp_count} components")

        for sheet_name in last_sheets:
            if sheet_name not in current_sheets:
                self._notify_log(f"Removed sheet {sheet_name}")

    def _update_hierarchical_changelog(self, project_path: Path, hier: HierarchicalSchematic,
                                        current_state: Dict[str, Any], reason: str, is_initial: bool):
        """Update the changelog file with hierarchical changes."""
        changelog_path = project_path / "netlist_changelog.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(changelog_path, 'a', encoding='utf-8') as f:
                f.write(f"\n[{timestamp}] {reason}\n")

                if is_initial:
                    f.write(f"  + Initial hierarchical generation\n")
                    f.write(f"    - {len(hier.all_components)} components\n")
                    f.write(f"    - {len(hier.sheets)} sheets\n")
                    for path, sch in hier.sheets:
                        f.write(f"      {path}: {len(sch.components)} components\n")
                elif self.last_generation_state:
                    # Write detailed changes to changelog
                    changes = []

                    # Component changes
                    current_components = current_state.get("components", {})
                    last_components = self.last_generation_state.get("components", {})

                    for ref, comp_data in current_components.items():
                        if ref not in last_components:
                            changes.append(f"  + Added component {ref}: {comp_data['value']}")
                        elif comp_data != last_components[ref]:
                            old_value = last_components[ref]['value']
                            new_value = comp_data['value']
                            if old_value != new_value:
                                changes.append(f"  * Modified component {ref}: {old_value} → {new_value}")
                            else:
                                changes.append(f"  * Modified component {ref} footprint")

                    for ref in last_components:
                        if ref not in current_components:
                            changes.append(f"  - Removed component {ref}")

                    # Sheet changes
                    current_sheets = dict(current_state.get("sheets", []))
                    last_sheets = dict(self.last_generation_state.get("sheets", []))

                    for sheet_name, comp_count in current_sheets.items():
                        if sheet_name not in last_sheets:
                            changes.append(f"  + Added sheet {sheet_name} ({comp_count} components)")
                        elif comp_count != last_sheets[sheet_name]:
                            changes.append(f"  * Modified sheet {sheet_name}: {last_sheets[sheet_name]} → {comp_count} components")

                    for sheet_name in last_sheets:
                        if sheet_name not in current_sheets:
                            changes.append(f"  - Removed sheet {sheet_name}")

                    if changes:
                        for change in changes:
                            f.write(f"{change}\n")
                    else:
                        f.write("  No changes detected\n")

        except Exception as e:
            self._notify_log(f"Failed to update changelog: {e}")


# Global service instance
_netlist_service: Optional[NetlistService] = None


def get_netlist_service() -> NetlistService:
    """Get the global netlist service instance."""
    global _netlist_service
    if _netlist_service is None:
        _netlist_service = NetlistService()
    return _netlist_service

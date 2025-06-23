"""Shared state management between GUI and tray applications."""

import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .tokenizer import TokenStats


@dataclass
class AppState:
    """Shared application state."""
    project_path: Optional[str] = None
    output_file: str = "netlist_summary.txt"
    monitoring: bool = False
    update_interval: int = 30
    last_update: Optional[str] = None
    token_stats: Optional[Dict[str, Any]] = None
    component_count: int = 0
    net_count: int = 0
    connection_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppState':
        """Create from dictionary."""
        return cls(**data)


class SharedStateManager:
    """Manages shared state between GUI and tray applications."""
    
    def __init__(self, state_file: Optional[Path] = None):
        if state_file is None:
            # Use a standard location in user's home directory
            home_dir = Path.home()
            state_dir = home_dir / ".kicad_netlist_tool"
            state_dir.mkdir(exist_ok=True)
            self.state_file = state_dir / "app_state.json"
        else:
            self.state_file = state_file
        
        self._state = AppState()
        self._lock = threading.Lock()
        self._load_state()
    
    def _load_state(self):
        """Load state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                self._state = AppState.from_dict(data)
        except Exception:
            # If loading fails, use default state
            self._state = AppState()
    
    def _save_state(self):
        """Save state to file."""
        try:
            self.state_file.parent.mkdir(exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self._state.to_dict(), f, indent=2)
        except Exception:
            # Silently fail if we can't save state
            pass
    
    def get_state(self) -> AppState:
        """Get a copy of the current state."""
        with self._lock:
            # Create a new instance to avoid external modification
            return AppState.from_dict(self._state.to_dict())
    
    def update_project_path(self, path: Optional[Path]):
        """Update the project path."""
        with self._lock:
            self._state.project_path = str(path) if path else None
            self._save_state()
    
    def update_monitoring(self, monitoring: bool):
        """Update monitoring status."""
        with self._lock:
            self._state.monitoring = monitoring
            self._save_state()
    
    def update_interval(self, interval: int):
        """Update the monitoring interval."""
        with self._lock:
            self._state.update_interval = interval
            self._save_state()
    
    def update_output_file(self, filename: str):
        """Update the output filename."""
        with self._lock:
            self._state.output_file = filename
            self._save_state()
    
    def update_stats(self, token_stats: TokenStats, component_count: int, 
                    net_count: int, connection_count: int):
        """Update statistics."""
        with self._lock:
            self._state.token_stats = {
                'original_tokens': token_stats.original_tokens,
                'compressed_tokens': token_stats.compressed_tokens,
                'original_size': token_stats.original_size,
                'compressed_size': token_stats.compressed_size,
                'file_count': token_stats.file_count,
                'token_reduction': token_stats.token_reduction,
                'size_reduction': token_stats.size_reduction
            }
            self._state.component_count = component_count
            self._state.net_count = net_count
            self._state.connection_count = connection_count
            self._state.last_update = datetime.now().isoformat()
            self._save_state()
    
    def mark_update(self):
        """Mark that an update occurred."""
        with self._lock:
            self._state.last_update = datetime.now().isoformat()
            self._save_state()
    
    def get_project_path(self) -> Optional[Path]:
        """Get the current project path."""
        state = self.get_state()
        return Path(state.project_path) if state.project_path else None
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self.get_state().monitoring
    
    def get_stats_summary(self) -> str:
        """Get a formatted stats summary."""
        state = self.get_state()
        if not state.token_stats:
            return "No statistics available"
        
        stats = state.token_stats
        return (
            f"Token Reduction: {stats['token_reduction']:.1f}%\n"
            f"Original: {stats['original_tokens']:,} tokens\n"
            f"Compressed: {stats['compressed_tokens']:,} tokens\n"
            f"Components: {state.component_count}\n"
            f"Nets: {state.net_count}\n"
            f"Connections: {state.connection_count}"
        )
    
    def clear_state(self):
        """Clear all state (useful for testing)."""
        with self._lock:
            self._state = AppState()
            self._save_state()


# Global instance for shared use
_shared_state_manager: Optional[SharedStateManager] = None


def get_shared_state() -> SharedStateManager:
    """Get the global shared state manager."""
    global _shared_state_manager
    if _shared_state_manager is None:
        _shared_state_manager = SharedStateManager()
    return _shared_state_manager


def set_shared_state_file(state_file: Path):
    """Set a custom state file (useful for testing)."""
    global _shared_state_manager
    _shared_state_manager = SharedStateManager(state_file)
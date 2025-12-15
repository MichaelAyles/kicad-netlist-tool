"""System tray application for KiCad Netlist Tool - Main Entry Point."""

import threading
import time
from pathlib import Path
from typing import Optional

# Only import tkinter on Linux as fallback, avoid on macOS/Windows
import sys
if sys.platform not in ["darwin", "win32"]:
    try:
        import tkinter as tk
        from tkinter import messagebox, filedialog
        TKINTER_AVAILABLE = True
    except ImportError:
        TKINTER_AVAILABLE = False
else:
    TKINTER_AVAILABLE = False

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as Item

from ..service import get_netlist_service
from ..shared_state import get_shared_state


class TrayIcon:
    """System tray icon for KiCad Netlist Tool."""
    
    def __init__(self):
        self.icon: Optional[pystray.Icon] = None
        self.service = get_netlist_service()
        self.shared_state = get_shared_state()
        self.current_status = "idle"
        
        # Register callbacks with the service
        self.service.add_status_callback(self.on_status_change)
        self.service.add_log_callback(self.on_log_message)
        
        # Start the service
        self.service.start()
        
        # Create the tray icon
        self.setup_icon()
    
    def on_status_change(self, status: str):
        """Handle status changes from the service."""
        if status.lower().find("monitoring") != -1 or status.lower().find("watching") != -1:
            self.current_status = "watching"
        elif status.lower().find("generating") != -1 or status.lower().find("processing") != -1:
            self.current_status = "processing"
        elif status.lower().find("error") != -1:
            self.current_status = "error"
        elif status.lower().find("ready") != -1:
            self.current_status = "success" if self.service.is_monitoring() else "idle"
        else:
            self.current_status = "idle"
            
        self.update_icon_status(self.current_status)
    
    def on_log_message(self, message: str):
        """Handle log messages from the service."""
        # For tray app, we can show important messages as notifications
        if "error" in message.lower():
            # Extract just the message part (remove timestamp)
            clean_message = message.split("] ", 1)[-1] if "] " in message else message
            self.show_notification("Error", clean_message)
        elif "generated netlist" in message.lower():
            # Show success notifications for netlist generation
            clean_message = message.split("] ", 1)[-1] if "] " in message else message
            self.show_notification("Netlist Updated", clean_message)
    
    def create_icon_image(self, status="idle"):
        """Create the tray icon image."""
        # Create a 64x64 image with transparency
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Define colors based on status
        colors = {
            "idle": "#666666",      # Gray
            "watching": "#2196F3",  # Blue  
            "processing": "#FF9800", # Orange
            "success": "#4CAF50",   # Green
            "error": "#F44336"      # Red
        }
        
        color = colors.get(status, colors["idle"])
        
        # Draw a circle for the main icon
        draw.ellipse([8, 8, 56, 56], fill=color, outline="#FFFFFF", width=2)
        
        # Add status indicator
        if status == "watching":
            # Add small dots to indicate activity
            draw.ellipse([45, 15, 52, 22], fill="#FFFFFF")
            draw.ellipse([45, 42, 52, 49], fill="#FFFFFF")
        elif status == "processing":
            # Add gear-like pattern
            for i in range(8):
                angle = i * 45
                x = 32 + 12 * (1 if i % 2 else 0.7)
                y = 32 + 12 * (1 if i % 2 else 0.7)
                draw.ellipse([x-2, y-2, x+2, y+2], fill="#FFFFFF")
        elif status == "success":
            # Add checkmark
            draw.line([22, 32, 28, 38], fill="#FFFFFF", width=3)
            draw.line([28, 38, 42, 24], fill="#FFFFFF", width=3)
        
        # Add "K" for KiCad in the center
        draw.text((24, 20), "K", fill="#FFFFFF", font_size=24)
        
        return image
    
    def setup_icon(self):
        """Setup the system tray icon."""
        icon_image = self.create_icon_image("idle")
        
        menu = pystray.Menu(
            Item("KiCad Netlist Tool", self.show_about, default=True),
            Item("────────────────", lambda: None, enabled=False),
            Item("Open GUI", self.show_gui),
            Item("Select Project...", self.select_project),
            pystray.Menu.SEPARATOR,
            Item("Start Monitoring", self.toggle_monitoring, checked=lambda item: self.service.is_monitoring()),
            Item("Generate Once", self.generate_once, enabled=lambda item: self.service.get_project_path() is not None),
            pystray.Menu.SEPARATOR,
            Item("Statistics", self.show_statistics),
            Item("Open Output", self.open_output, enabled=lambda item: self.service.get_project_path() is not None),
            pystray.Menu.SEPARATOR,
            Item("Exit", self.quit_application)
        )
        
        self.icon = pystray.Icon(
            "kicad_netlist_tool",
            icon_image,
            "KiCad Netlist Tool",
            menu
        )
    
    def update_icon_status(self, status="idle"):
        """Update the tray icon to reflect current status."""
        if self.icon:
            self.icon.icon = self.create_icon_image(status)
    
    def show_notification(self, title: str, message: str):
        """Show a system notification."""
        if self.icon:
            self.icon.notify(message, title)
    
    def show_about(self, icon=None, item=None):
        """Show about information."""
        summary = self.service.get_status_summary()
        stats_info = ""
        if summary['statistics']:
            reduction = summary['statistics'].get('token_reduction', 0)
            stats_info = f"\\n\\nLast Analysis:\\n{reduction:.1f}% token reduction"
        
        project_name = "None"
        if summary['project_path']:
            project_name = Path(summary['project_path']).name
        
        message = (f"KiCad Netlist Tool v1.0\\n\\n"
                  f"Running as background service\\n"
                  f"Status: {'Monitoring' if summary['monitoring'] else 'Idle'}\\n"
                  f"Project: {project_name}"
                  f"{stats_info}")
        
        self.show_native_dialog("KiCad Netlist Tool", message)
    
    def show_gui(self, icon=None, item=None):
        """Show the main GUI window."""
        import subprocess
        import sys
        
        try:
            # Launch GUI as a separate process instead of thread to avoid tkinter/macOS issues
            cmd = [sys.executable, "-m", "kicad_netlist_tool", "gui"]
            subprocess.Popen(cmd)
            
            self.show_notification(
                "GUI Launched",
                "Main GUI window has been opened"
            )
        except Exception as e:
            self.show_notification("Error", f"Failed to launch GUI: {e}")
    
    def select_project(self, icon=None, item=None):
        """Select a project directory."""
        try:
            # Use the system file dialog instead of tkinter to avoid compatibility issues
            import subprocess
            import sys
            
            if sys.platform == "darwin":  # macOS
                # Use osascript to show native folder picker
                script = '''
                tell application "System Events"
                    activate
                    set chosenFolder to choose folder with prompt "Select KiCad Project Directory"
                    return POSIX path of chosenFolder
                end tell
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    directory = result.stdout.strip()
                else:
                    return  # User cancelled
                    
            elif sys.platform == "win32":  # Windows
                # Use PowerShell folder picker
                script = '''
                Add-Type -AssemblyName System.Windows.Forms
                $browser = New-Object System.Windows.Forms.FolderBrowserDialog
                $browser.Description = "Select KiCad Project Directory"
                $browser.RootFolder = "MyComputer"
                if($browser.ShowDialog() -eq "OK") {
                    $browser.SelectedPath
                }
                '''
                result = subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    directory = result.stdout.strip()
                else:
                    return  # User cancelled
                    
            else:  # Linux - fall back to tkinter if available
                if TKINTER_AVAILABLE:
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    
                    directory = filedialog.askdirectory(
                        title="Select KiCad Project Directory",
                        initialdir=str(self.project_path) if self.project_path else str(Path.home())
                    )
                    root.destroy()
                    
                    if not directory:
                        return
                else:
                    self.show_notification("Error", "No file dialog available. Please use the GUI instead.")
                    return
            
            # Set the selected directory using the service
            project_path = Path(directory)
            if self.service.set_project_path(project_path):
                self.show_notification(
                    "Project Selected",
                    f"Project set: {project_path.name}"
                )
                
                # Auto-start monitoring if not already running
                if not self.service.is_monitoring():
                    self.service.start_monitoring()
            else:
                self.show_notification(
                    "Error",
                    f"Invalid project directory: {project_path.name}"
                )
                
        except Exception as e:
            self.show_notification("Error", f"Failed to select project: {e}")
    
    def toggle_monitoring(self, icon=None, item=None):
        """Toggle monitoring on/off."""
        if self.service.is_monitoring():
            self.service.stop_monitoring()
        else:
            if self.service.get_project_path():
                self.service.start_monitoring()
            else:
                self.show_notification("Error", "Please select a project directory first")
    
    def generate_once(self, icon=None, item=None):
        """Generate netlist once."""
        if not self.service.get_project_path():
            self.show_notification("Error", "Please select a project directory first")
            return
        
        self.service.generate_netlist("Manual generation")
    
    def show_statistics(self, icon=None, item=None):
        """Show current statistics."""
        stats_text = self.shared_state.get_stats_summary().replace('\n', '\\n')
        self.show_native_dialog("Statistics", stats_text)
    
    def show_native_dialog(self, title: str, message: str):
        """Show a native dialog box for the current platform."""
        import subprocess
        import sys
        
        try:
            if sys.platform == "darwin":  # macOS
                # Use osascript for native dialog
                script = f'''
                tell application "System Events"
                    activate
                    display dialog "{message}" with title "{title}" buttons {{"OK"}} default button 1
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=False)
                
            elif sys.platform == "win32":  # Windows
                # Use PowerShell for native dialog
                script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.MessageBox]::Show("{message}", "{title}")
                '''
                subprocess.run(["powershell", "-Command", script], check=False)
                
            else:  # Linux - fallback to notification
                self.show_notification(title, message)
                
        except Exception:
            # Fallback to notification if dialog fails
            self.show_notification(title, message)
    
    def open_output(self, icon=None, item=None):
        """Open the output file."""
        project_path = self.service.get_project_path()
        if not project_path:
            return
        
        state = self.shared_state.get_state()
        output_path = project_path / state.output_file
        if output_path.exists():
            import subprocess
            import sys
            
            try:
                if sys.platform == "win32":
                    subprocess.run(["notepad", str(output_path)])
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(output_path)])
                else:
                    subprocess.run(["xdg-open", str(output_path)])
            except Exception as e:
                self.show_notification("Error", f"Could not open file: {e}")
        else:
            self.show_notification("Warning", "Output file does not exist yet")
    
    def quit_application(self, icon=None, item=None):
        """Quit the application."""
        # Unregister callbacks
        self.service.remove_status_callback(self.on_status_change)
        self.service.remove_log_callback(self.on_log_message)
        
        # Stop the service
        self.service.stop()
        
        if self.icon:
            self.icon.stop()
    
    def run(self):
        """Run the tray application."""
        if self.icon:
            self.icon.run()


def main():
    """Main entry point for tray application."""
    app = TrayIcon()
    app.run()


if __name__ == "__main__":
    main()
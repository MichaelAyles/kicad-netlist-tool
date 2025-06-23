# KiCad Netlist Tool - System Tray Application

The system tray application allows KiCad Netlist Tool to run silently in the background, automatically monitoring your KiCad projects and providing instant notifications when netlists are updated.

## 🔔 **Background Monitoring**

Perfect for developers who want seamless integration with their KiCad workflow without keeping a GUI window open.

## 🚀 **Quick Start**

### Launch Tray Application
```bash
# Start the system tray application
kicad-netlist-tray

# Or via CLI
python -m kicad_netlist_tool tray
```

### What You'll See
- **Windows**: Small KiCad icon in the system tray (bottom-right corner)
- **macOS**: KiCad icon in the menu bar (top-right corner)  
- **Linux**: Icon in the system tray/notification area

## 🖱️ **Using the Tray Icon**

### Right-Click Context Menu
| Menu Item | Function |
|-----------|----------|
| **KiCad Netlist Tool** | Show about information (default action) |
| **Open GUI** | Launch the full GUI interface |
| **Select Project...** | Choose KiCad project directory |
| **Start Monitoring** | Toggle automatic file watching (✓ when active) |
| **Generate Once** | Create netlist without starting monitoring |
| **Statistics** | View current token reduction stats |
| **Open Output** | Launch netlist summary file in default editor |
| **Exit** | Close the tray application |

### Icon Status Indicators
- **Gray Circle**: Idle - not monitoring
- **Blue Circle with Dots**: Watching for file changes
- **Orange Circle with Gear**: Processing files
- **Green Circle with Checkmark**: Success (briefly shown)
- **Red Circle**: Error occurred

## 🔄 **Automatic Workflow**

### Typical Usage:
1. **Launch tray app**: `kicad-netlist-tray`
2. **Right-click → Select Project**: Choose your KiCad project folder
3. **Monitoring starts automatically** when project is selected
4. **Work normally in KiCad** - edit schematics, save changes
5. **Get instant notifications** when netlists are updated
6. **View statistics** anytime via right-click menu

### What Happens Automatically:
- ✅ **File Detection**: Monitors all `.kicad_sch` files in project directory
- ✅ **Change Detection**: Detects when schematic files are saved
- ✅ **Automatic Processing**: Generates updated netlist summary
- ✅ **Token Analysis**: Calculates reduction statistics
- ✅ **Notifications**: Shows system notifications with results
- ✅ **File Updates**: Updates `netlist_summary.txt` and `netlist_changelog.txt`

## 📊 **Notifications**

### Notification Types:
- **Project Selected**: "Now monitoring: [project_name]"
- **Monitoring Started**: "Watching [project_name] for changes"
- **Netlist Updated**: "24 components, 15 nets - Token reduction: 96.5%"
- **Monitoring Stopped**: "File watching has been disabled"
- **Errors**: "Failed to generate netlist: [error_message]"

### Notification Timing:
- Shown for 5-10 seconds (system dependent)
- Non-intrusive - won't interrupt your work
- Click to dismiss early (on most systems)

## ⚙️ **Configuration**

### Monitoring Interval
- **Default**: 30 seconds between file checks
- **Configurable**: Can be adjusted in the full GUI application
- **Efficient**: Only processes when files actually change

### File Locations
All files are created in your selected project directory:
- `netlist_summary.txt` - Main netlist output
- `netlist_changelog.txt` - Detailed change history

## 🔗 **Integration with GUI**

### Launching from GUI:
- **Options → Start Tray Application**: Launch tray app from GUI
- **Options → Minimize to Tray**: Offers to start tray app when minimizing
- **Seamless Handoff**: Both apps can work with the same project

### Running Both:
- ✅ **Safe**: GUI and tray app can run simultaneously
- ✅ **Synchronized**: Both work with the same project files
- ✅ **Independent**: Each has its own monitoring settings

## 🔧 **Troubleshooting**

### Common Issues:

1. **Icon doesn't appear**
   - Check system tray settings (Windows: Show hidden icons)
   - Restart the application
   - Try `python -m kicad_netlist_tool tray` for error messages

2. **No notifications**
   - Check system notification settings
   - Verify project directory is selected
   - Ensure monitoring is enabled (✓ in context menu)

3. **Files not updating**
   - Confirm you're saving files in KiCad (Ctrl+S)
   - Check that selected directory contains `.kicad_sch` files
   - Right-click icon → Statistics to verify project is loaded

4. **Application won't start**
   - Install dependencies: `pip install pystray Pillow`
   - Check Python version compatibility (3.8+)
   - Try the GUI version first: `kicad-netlist-gui`

### Platform-Specific Notes:

#### Windows
- Icon appears in system tray (bottom-right)
- May be hidden - click "Show hidden icons" (^) 
- Notifications appear as Windows toast notifications
- Default editor: Notepad

#### macOS  
- Icon appears in menu bar (top-right)
- Notifications appear as macOS notifications
- Default editor: TextEdit (via `open` command)
- May require accessibility permissions for notifications

#### Linux
- Icon location varies by desktop environment
- Notifications use system notification daemon
- Default editor: via `xdg-open`
- Requires notification support (`libnotify` or similar)

## 💡 **Pro Tips**

### Workflow Optimization:
1. **Start with project**: Launch tray app → select project → automatic monitoring
2. **Use with version control**: Changelog tracks every change for commit messages
3. **Check statistics**: Right-click → Statistics shows current reduction metrics
4. **Multiple projects**: Easily switch between projects via Select Project menu

### Best Practices:
- **Keep running**: Tray app uses minimal resources when idle
- **Check notifications**: Confirms successful netlist generation
- **Use output files**: Share `netlist_summary.txt` with team/LLMs
- **Monitor changelog**: Track circuit evolution in `netlist_changelog.txt`

### Resource Usage:
- **CPU**: Near-zero when idle, brief spike during processing
- **Memory**: ~10-20MB typical usage
- **Disk**: Only writes when changes detected
- **Network**: No network usage

## 🎯 **Perfect For:**

- **Background Development**: Work in KiCad without thinking about netlist updates
- **Team Collaboration**: Automatic generation of shareable netlists
- **LLM Workflows**: Always-current, token-efficient circuit documentation
- **Version Control**: Automatic changelog for tracking circuit changes
- **Multi-Project Work**: Easy switching between different KiCad projects

The tray application transforms KiCad Netlist Tool from a manual utility into an automatic, background service that seamlessly integrates with your PCB design workflow!
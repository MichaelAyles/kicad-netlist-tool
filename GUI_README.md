# KiCad Netlist Tool - GUI Application

Since KiCad doesn't currently support Python plugins for Eeschema (schematic editor), we've created a standalone GUI application that runs alongside KiCad to provide seamless netlist extraction.

## Features

### 🖥️ **Easy-to-Use GUI Interface**
- Simple point-and-click operation
- Real-time status updates
- Built-in log viewer
- Always-on-top option for easy access

### 🔄 **Automatic File Watching**
- Monitors KiCad project directory for schematic changes
- Configurable update interval (5-300 seconds)
- Automatic netlist regeneration when files change
- Works with multiple schematic files in a project

### 📊 **Changelog Tracking**
- Automatically tracks all changes to components and nets
- Timestamps every modification
- Shows added/removed/modified components and nets
- Separate changelog file for complete audit trail

### 📁 **Output Management**
- Generates `netlist_summary.txt` with component and net information
- Creates `netlist_changelog.txt` with detailed change history
- Built-in file opening integration
- Customizable output file names

## Installation

```bash
# Install the tool (if not already installed)
pip install -e .

# The GUI launcher is now available as:
kicad-netlist-gui

# Or use the CLI command:
python -m kicad_netlist_tool gui
```

## Usage

### 1. **Launch the GUI**
```bash
kicad-netlist-gui
```

### 2. **Select Your KiCad Project**
- Click "Browse..." to select your KiCad project directory
- The tool will automatically detect all `.kicad_sch` files
- Output files will be created in the same directory

### 3. **Configure Settings**
- Set update interval (default: 30 seconds)
- Customize output filename if needed
- Enable "Always on Top" for easy access while working in KiCad

### 4. **Start Monitoring**
- Click "Start Watching" to begin automatic monitoring
- The tool will generate an initial netlist and begin watching for changes
- Any modifications to schematic files will trigger automatic updates

### 5. **View Results**
- Click "Open Output" to view the current netlist summary
- Click "View Changelog" to see the complete change history
- Monitor the log area for real-time status updates

## GUI Controls

| Button | Function |
|--------|----------|
| **Browse...** | Select KiCad project directory |
| **Start/Stop Watching** | Toggle automatic file monitoring |
| **Generate Once** | Create netlist without starting continuous monitoring |
| **Open Output** | Open the netlist summary file in your default text editor |
| **View Changelog** | Display the changelog in a separate window |

## Menu Options

### File Menu
- **Open Project Directory...** - Select KiCad project folder
- **Exit** - Close the application

### Options Menu
- **Always on Top** - Keep the GUI window above all other windows

### Help Menu
- **About** - Show version and information

## Workflow Integration

### Typical Workflow:
1. **Open KiCad** and load your project
2. **Launch the GUI tool** (`kicad-netlist-gui`)
3. **Select your project directory** in the GUI
4. **Click "Start Watching"**
5. **Work normally in KiCad** - edit schematics, add components, modify connections
6. **The tool automatically updates** the netlist summary every time you save changes
7. **Use the netlist files** for LLM documentation, version control, or analysis

### Desktop Integration

On Linux, you can install the desktop launcher:
```bash
# Copy the desktop file to applications directory
cp KiCadNetlistTool.desktop ~/.local/share/applications/

# Make it executable
chmod +x ~/.local/share/applications/KiCadNetlistTool.desktop
```

This will add "KiCad Netlist Tool" to your applications menu.

## Output Files

### `netlist_summary.txt`
Contains the compact netlist information:
```
# KiCad Netlist Summary

## Components
- U1: ECC83 (Footprints:Valve_ECC-83-1)
- R1: 1.5K (Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal)
...

## Nets
- Net_1: C2.1, P2.2, R3.2
- Net_5: P1.1, R4.2
...

## Summary
- Components: 24
- Nets: 15
- Total connections: 29
```

### `netlist_changelog.txt`
Tracks all changes with timestamps:
```
[2024-01-15 14:30:22] Initial netlist generation
  + Initial netlist generation
    - 24 components
    - 15 nets

[2024-01-15 14:35:18] Schematic file changed
  + Added component R5: 10K
  * Modified net Net_1 (4 connections)
  
[2024-01-15 14:40:05] Schematic file changed
  - Removed component C3
  + Added net Net_16 (2 connections)
```

## Technical Details

- **Built with tkinter** for cross-platform compatibility
- **Thread-based file monitoring** for responsive GUI
- **Intelligent change detection** to avoid unnecessary updates
- **Robust error handling** with user-friendly messages
- **Memory efficient** - only processes files when changes detected

## Troubleshooting

### Common Issues:

1. **"No .kicad_sch files found"**
   - Ensure you've selected the correct project directory
   - Check that your schematic files have the `.kicad_sch` extension

2. **Changes not detected**
   - Verify the update interval isn't too long
   - Make sure you're saving files in KiCad (Ctrl+S)
   - Check the log area for error messages

3. **Permission errors**
   - Ensure the tool has write permissions to the project directory
   - Try running from a directory you own

4. **GUI doesn't start**
   - Ensure tkinter is installed: `python -c "import tkinter"`
   - Try the CLI version: `python -m kicad_netlist_tool parse your_file.kicad_sch`

## Integration with LLMs

The generated netlist files are optimized for LLM consumption:
- **96%+ token reduction** compared to raw KiCad files
- **Structured format** that's easy for LLMs to parse
- **Complete connectivity information** for circuit analysis
- **Change tracking** for version-aware documentation

Perfect for including in Claude Code conversations, ChatGPT analysis, or automated documentation workflows!
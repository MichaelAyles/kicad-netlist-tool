# KiCad Netlist Tool

A lightweight background service and GUI tool to extract component and netlist information from KiCad schematic files in a token-efficient format for LLM documentation.

## Problem

KiCad schematic files (.kicad_sch) contain extensive formatting and graphical information that makes them token-intensive for LLM processing. For example, a typical schematic file can be 55KB+ on disk and require 25,000+ tokens. This tool extracts only the essential information needed for documentation:
- Component references and values
- Pin connections and net connectivity  
- Circuit topology and relationships

## Token Reduction

**Dramatic token savings**: Achieves 96%+ token reduction while preserving complete circuit connectivity information. Example: 26,000 tokens → 453 tokens (98.3% reduction).

## Architecture

- **Background Service**: Core `NetlistService` handles all processing, monitoring, and state management
- **System Tray**: Main entry point providing always-available background monitoring
- **GUI Interface**: On-demand detailed interface with real-time statistics
- **Shared State**: Perfect synchronization between tray and GUI interfaces

## Features

### Core Features
- Parse KiCad schematic files (.kicad_sch) with complete net extraction
- Real-time file monitoring with configurable intervals (5-300 seconds)
- Intelligent change detection (initial vs. no-change vs. actual changes)
- Automatic changelog generation tracking component/net additions/modifications
- Cross-platform support (Windows, macOS, Linux)

### User Experience
- **System Tray Integration**: Background monitoring with native notifications
- **GUI Interface**: Beautiful statistics panel with before/after token counts
- **Smart Logging**: Detailed change tracking ("Added component U1: 74AHC04")
- **Project Management**: Easy directory navigation and file access
- **Token Statistics**: Real-time reduction percentages and savings calculations

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/kicad-netlist-tool.git
cd kicad-netlist-tool

# Install the tool
pip install -e .
```

## Usage

### Main Application (Recommended)
```bash
# Launch the main application (system tray with background service)
kicad-netlist-tool
```

This starts the background service with system tray integration. The tray provides:
- **Background Monitoring**: Automatic file watching and netlist updates
- **Native Notifications**: Cross-platform notifications for changes
- **GUI Access**: Right-click menu option to open the detailed GUI interface
- **Project Management**: Easy project directory selection and settings

### Application Interfaces

#### System Tray (Always Available)
- 🟢 **Background Service**: Runs continuously monitoring your KiCad project
- 🔔 **Smart Notifications**: "Added component U1: 74AHC04" style change alerts
- 📁 **Project Selection**: Native file dialogs for directory selection
- ⚙️ **Quick Controls**: Start/stop monitoring, generate once, view statistics

#### GUI Interface (On-Demand)
Launch from tray menu → "Open GUI" or directly via:
```bash
# Direct GUI launch (connects to running service)
python -m kicad_netlist_tool.gui.main_window
```

**GUI Features:**
- 📊 **Beautiful Statistics Panel**: Before/after token counts with reduction percentages
- 📈 **Real-time Updates**: Live statistics as files change
- 📝 **Detailed Logging**: Component-level change tracking with timestamps
- 🗂️ **File Management**: Integrated project navigation and output file access
- 📋 **Changelog Viewer**: Built-in changelog browser with change history

### State Synchronization
Both tray and GUI interfaces share the same background service, providing:
- **Unified State**: Changes in one interface appear in the other
- **Seamless Switching**: Close GUI, continue in tray; reopen GUI to see current status
- **Persistent Settings**: Project path, monitoring status, and statistics persist across sessions

## Output Files

### Netlist Summary (`netlist_summary.txt`)
The tool generates a concise text file with components and complete net connectivity:
```
# KiCad Netlist Summary

## Components
- U1: ECC83 (Footprints:Valve_ECC-83-1)
- R1: 1.5K (Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal)
- C1: 10uF (Capacitor_THT:CP_Radial_D10.0mm_P5.00mm)
- P1: IN (Footprints:Altech_AK300_1x02_P5.00mm_45-Degree)
...

## Nets
- Net_1: C2.1, P2.2, R3.2
- Net_5: P1.1, R4.2
- Net_7: C2.2, R1.1
...

## Summary
- Components: 24
- Nets: 15
- Total connections: 29
```

### Changelog (`netlist_changelog.txt`)
Automatic change tracking with detailed component/net modifications:
```
[2025-06-23 14:30:17] Initial generation
  + Initial netlist generation
    - 24 components
    - 15 nets

[2025-06-23 14:45:22] Schematic file changed
  + Added component U2: 74AHC244
  * Modified component R1: 1K → 1.2K
  + Added net Net_16 (3 connections)
  - Removed net Net_14

[2025-06-23 14:50:33] Manual generation
  No changes detected
```

### Change Detection Intelligence
- **Initial Generation**: "Initial netlist generation: X components, Y nets"
- **No Changes**: "Netlist regenerated, no changes detected"
- **Actual Changes**: Detailed logging of additions, modifications, and removals

## Quick Start

1. **Install**: `pip install -e .`
2. **Launch**: `kicad-netlist-tool` (starts system tray)
3. **Select Project**: Right-click tray icon → "Select Project..."
4. **Start Monitoring**: Right-click tray icon → "Start Monitoring" 
5. **View Results**: Right-click tray icon → "Open GUI" for detailed view

The tool will automatically:
- Generate `netlist_summary.txt` with token-efficient circuit data
- Create `netlist_changelog.txt` tracking all changes
- Monitor files and update when schematics are modified
- Show notifications for component additions/changes

## Benefits for LLM Documentation

- **Massive Token Savings**: 96%+ reduction in token usage
- **Complete Connectivity**: All component connections preserved
- **Change Tracking**: Detailed logs of circuit modifications
- **Real-time Updates**: Always current with your design
- **Background Operation**: Works invisibly while you design

Perfect for including KiCad circuits in:
- 📖 Technical documentation
- 🤖 LLM conversations about your designs  
- 📋 Design reviews and collaboration
- 🔄 Automated documentation workflows

## Development

```bash
# Run tests
pytest

# Format code  
black .

# Lint
ruff check .
```

## License

MIT License - see LICENSE file
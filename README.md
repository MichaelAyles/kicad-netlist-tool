# KiCad Netlist Tool

A lightweight tool to extract component and netlist information from KiCad schematic files in a token-efficient format for LLM documentation.

## Problem

KiCad schematic files (.kicad_sch) contain extensive formatting and graphical information that makes them token-intensive for LLM processing. For example, the ECC83-pp example schematic included with this tool is 55KB on disk and requires 26,000 tokens using the OpenAI tokenizer. This tool extracts only the essential information needed for documentation:
- Component references and values
- Pin connections  
- Net names and connectivity

## Token Reduction

**Dramatic token savings**: The ECC83-pp example file is reduced from 26,000 tokens to just 866 tokens (96.7% reduction) while preserving all essential circuit information.

## Features

- Parse KiCad schematic files (.kicad_sch)
- Extract component information (reference, value, footprint)
- Map pin connections and net names
- Output in compact, LLM-friendly format
- Optional real-time file watching for automatic updates
- Significantly reduce token usage (96%+ reduction demonstrated)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/kicad-netlist-tool.git
cd kicad-netlist-tool

# Install the tool
pip install -e .
```

## Usage

### GUI Application (Recommended)
```bash
# Launch the GUI interface
kicad-netlist-gui

# Or via CLI
python -m kicad_netlist_tool gui
```

**Features:**
- 🖥️ Easy point-and-click interface
- 🔄 Automatic file watching with configurable intervals
- 📊 Built-in changelog tracking
- 📁 Integrated file management
- ⚙️ Always-on-top option for KiCad workflow integration

See [GUI_README.md](GUI_README.md) for detailed GUI usage instructions.

### Command Line Interface
```bash
# Parse a single schematic file
python -m kicad_netlist_tool parse path/to/your/schematic.kicad_sch

# Parse all schematics in a project
python -m kicad_netlist_tool parse path/to/your/project/

# Watch for changes and auto-update
python -m kicad_netlist_tool watch path/to/your/project/
```

### Output format
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
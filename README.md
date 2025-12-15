# KiCad Netlist Tool

Extract component and netlist information from KiCad schematics in TOKN format - a token-efficient representation optimized for LLM processing.

![KiCad Netlist Tool Screenshot](assets/screenshot.png)

## Token Reduction

KiCad schematic files contain extensive graphical and metadata information that consumes many tokens when used with LLMs. This tool extracts only the essential electrical information:

| Schematic | Raw File | TOKN Output | Reduction |
|-----------|----------|-------------|-----------|
| ECC83-pp | 55KB (26,000 tokens) | ~900 tokens | 96.5% |

## Installation

```bash
pip install -e .
```

## Usage

### GUI (Recommended)

```bash
kicad-netlist-gui
```

Features:
- **Smart project detection** - automatically finds the root schematic
- **Hierarchical sheet selection** - tree view with checkboxes to select specific sheets
- **Copy to clipboard** - for quick pasting into LLM conversations
- **Save to file** - exports as `.tokn` file
- **File monitoring** - watches for changes and auto-regenerates

> **Note:** The system tray icon has been temporarily removed pending cross-platform testing. The tool has been updated from the legacy format to use TOKN v1.2.

### Command Line

```bash
# Parse a project directory
python -m kicad_netlist_tool parse /path/to/project

# Watch for changes
python -m kicad_netlist_tool watch /path/to/project
```

## Output Format (TOKN v1.2)

TOKN (Token-Optimised KiCad Notation) preserves electrical connectivity and component layout while stripping unnecessary metadata.

```
# TOKN v1
title: Audio Preamp

components[3]{ref,type,value,fp,x,y,w,h,a}:
  U1,ECC83,ECC83-1,Valve,127.00,85.09,25.40,20.32,0
  R1,R,1.5k,0805,149.86,85.09,7.62,0.00,90
  C1,C,10uF,RadialD10,123.19,64.77,0.00,7.62,0

nets[2]{name,pins}:
  VIN,U1.2,C1.1
  VOUT,U1.7,R1.2
```

See `spec/TOKN-v1.md` for the full specification.

## Development

```bash
pytest          # Run tests
black .         # Format code
ruff check .    # Lint
mypy .          # Type check
```

## License

MIT

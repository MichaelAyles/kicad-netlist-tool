# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a KiCad netlist tool designed for extracting component and netlist information from KiCad schematic files in a token-efficient format for LLM automation of documentation. KiCad is an open-source EDA (Electronic Design Automation) software suite for electronic circuit design.

## Token Efficiency

This tool dramatically reduces token usage for LLM processing:
- **Example**: ECC83-pp schematic (55KB, 26,000 tokens) → 866 tokens (96.7% reduction)
- Preserves all essential circuit information: components, values, footprints, and complete net connectivity
- Enables cost-effective LLM analysis of large circuit designs

## Implementation Status

The tool is fully implemented with the following features:
- Complete KiCad .kicad_sch file parsing using S-expression format
- Library symbol extraction for pin definitions
- Wire tracing and net connectivity analysis
- Junction and label processing
- Multiple output formats (compact, markdown, JSON)
- File watching for real-time updates

### KiCad Netlist Context
- KiCad netlists are typically in XML format (.xml) or legacy format (.net)
- Netlists contain component references, values, footprints, and connection information
- Common use cases include BOM generation, documentation, and circuit analysis

### Suggested Development Approach

When implementing this tool, consider:
1. **Language Choice**: Python is commonly used for KiCad automation due to KiCad's Python API
2. **Key Features to Implement**:
   - Parse KiCad netlist files (XML and/or legacy format)
   - Extract component and connection data
   - Provide real-time monitoring of netlist file changes
   - Format data for LLM consumption

### Potential Project Structure
```
kicad-netlist-tool/
├── src/                 # Main source code
│   ├── parser/         # Netlist parsing logic
│   ├── monitor/        # File watching functionality
│   └── formatter/      # LLM-friendly output formatting
├── tests/              # Test files
├── examples/           # Example netlists and usage
└── docs/               # Additional documentation
```

## Development Commands

### Setup
- Install dependencies: `pip install -r requirements.txt`
- Install in development mode: `pip install -e .`

### Running the Tool

#### GUI Interface (Recommended)
- Launch GUI: `kicad-netlist-gui` or `python -m kicad_netlist_tool gui`
- Features: directory navigation, automatic file watching, changelog tracking, always-on-top option
- Quick access buttons for Examples, Home, and Current Directory

#### Command Line Interface  
- Parse single file: `python -m kicad_netlist_tool parse <schematic.kicad_sch>`
- Parse project: `python -m kicad_netlist_tool parse <project_directory>`
- Watch mode: `python -m kicad_netlist_tool watch <project_directory>`

### Development
- Run tests: `pytest`
- Lint: `ruff check .`
- Format: `black .`
- Type check: `mypy kicad_netlist_tool`

### File Watching
If implementing real-time monitoring, consider using:
- Python: `watchdog` library
- Node.js: `chokidar` or native `fs.watch`

## Important Considerations

1. **KiCad File Formats**: Be aware that KiCad file formats can vary between versions
2. **Performance**: Netlist files can be large for complex PCBs; consider streaming parsers
3. **LLM Integration**: Design output format to be easily consumable by LLMs (structured JSON, markdown tables, etc.)
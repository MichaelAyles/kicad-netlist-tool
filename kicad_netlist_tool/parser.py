"""Parser for KiCad schematic files (.kicad_sch)."""

# Re-export TOKN parser components for backward compatibility
from .tokn import (
    Schematic,
    Component,
    Wire,
    Junction,
    Label,
    LibSymbol,
    Pin,
    Point,
    parse_schematic,
    Netlist,
    Net,
    WireSegment,
    analyze_connectivity,
)

__all__ = [
    'Schematic',
    'Component',
    'Wire',
    'Junction',
    'Label',
    'LibSymbol',
    'Pin',
    'Point',
    'parse_schematic',
    'Netlist',
    'Net',
    'WireSegment',
    'analyze_connectivity',
]

"""TOKN - Token-Optimised KiCad Notation encoder."""

from .kicad_sch import (
    Schematic,
    Component,
    Wire,
    Junction,
    Label,
    LibSymbol,
    Pin,
    Point,
    HierarchicalSchematic,
    parse_schematic,
    parse_hierarchical_schematic,
    find_project_root,
)
from .connectivity import (
    Netlist,
    Net,
    WireSegment,
    analyze_connectivity,
    print_netlist,
)
from .encoder import (
    encode_tokn,
    encode_hierarchical_tokn,
    encode_sheet_tokn,
    convert_file,
    normalize_type,
    normalize_footprint,
)

__all__ = [
    # kicad_sch
    'Schematic',
    'Component',
    'Wire',
    'Junction',
    'Label',
    'LibSymbol',
    'Pin',
    'Point',
    'HierarchicalSchematic',
    'parse_schematic',
    'parse_hierarchical_schematic',
    'find_project_root',
    # connectivity
    'Netlist',
    'Net',
    'WireSegment',
    'analyze_connectivity',
    'print_netlist',
    # encoder
    'encode_tokn',
    'encode_hierarchical_tokn',
    'encode_sheet_tokn',
    'convert_file',
    'normalize_type',
    'normalize_footprint',
]

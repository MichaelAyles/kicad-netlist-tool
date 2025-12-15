"""Parser for KiCad schematic files (.kicad_sch)."""

# Import the enhanced parser
from .parser_v2 import EnhancedKiCadParser as KiCadSchematicParser, Component, Net

__all__ = ['KiCadSchematicParser', 'Component', 'Net']
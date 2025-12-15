"""Formatters for outputting component and netlist data."""

from typing import TextIO, List
from .tokn import (
    Schematic, Netlist, Net, Component, HierarchicalSchematic,
    encode_tokn, encode_hierarchical_tokn
)


class ToknFormatter:
    """Formats data in TOKN format (Token-Optimised KiCad Notation)."""

    @staticmethod
    def write(sch: Schematic, netlist: Netlist, output: TextIO):
        """Write schematic in TOKN format (flat/merged)."""
        tokn_output = encode_tokn(sch, netlist)
        output.write(tokn_output)

    @staticmethod
    def write_hierarchical(hier: HierarchicalSchematic, output: TextIO):
        """Write hierarchical schematic in TOKN format with per-sheet sections."""
        tokn_output = encode_hierarchical_tokn(hier)
        output.write(tokn_output)


class CompactFormatter:
    """Formats component and net data in a compact, LLM-friendly format (legacy)."""

    @staticmethod
    def write(components: List[Component], nets: List[Net], output: TextIO):
        """Write components and nets in compact format."""
        output.write("# KiCad Netlist Summary\n\n")

        # Write components section
        output.write("## Components\n")
        for comp in sorted(components, key=lambda c: c.reference):
            if comp.footprint:
                output.write(f"- {comp.reference}: {comp.value} ({comp.footprint})\n")
            else:
                output.write(f"- {comp.reference}: {comp.value}\n")

        output.write("\n")

        # Write nets section
        output.write("## Nets\n")
        for net in nets:
            if net.pins:
                connections = ", ".join([f"{ref}.{pin}" for ref, pin, _ in net.pins])
                output.write(f"- {net.name}: {connections}\n")
            else:
                output.write(f"- {net.name}: (no connections)\n")

        # Write summary
        output.write(f"\n## Summary\n")
        output.write(f"- Components: {len(components)}\n")
        output.write(f"- Nets: {len(nets)}\n")
        total_connections = sum(len(net.pins) for net in nets)
        output.write(f"- Total connections: {total_connections}\n")


class MarkdownFormatter:
    """Formats component and net data in detailed Markdown tables."""

    @staticmethod
    def write(components: List[Component], nets: List[Net], output: TextIO):
        """Write components and nets in Markdown table format."""
        output.write("# KiCad Netlist Documentation\n\n")

        # Component table
        output.write("## Components\n\n")
        output.write("| Reference | Value | Footprint | Library ID |\n")
        output.write("|-----------|-------|-----------|------------|\n")

        for comp in sorted(components, key=lambda c: c.reference):
            output.write(f"| {comp.reference} | {comp.value} | {comp.footprint or 'N/A'} | {comp.lib_id or 'N/A'} |\n")

        output.write("\n")

        # Net connections table
        output.write("## Net Connections\n\n")
        output.write("| Net Name | Connected Pins |\n")
        output.write("|----------|----------------|\n")

        for net in nets:
            if net.pins:
                connections = ", ".join([f"{ref}.{pin}" for ref, pin, _ in net.pins])
                output.write(f"| {net.name} | {connections} |\n")


class JsonFormatter:
    """Formats component and net data as JSON."""

    @staticmethod
    def write(components: List[Component], nets: List[Net], output: TextIO):
        """Write components and nets in JSON format."""
        import json

        data = {
            "components": {
                comp.reference: {
                    "value": comp.value,
                    "footprint": comp.footprint,
                    "lib_id": comp.lib_id,
                    "position": {"x": comp.x, "y": comp.y},
                    "angle": comp.angle,
                }
                for comp in components
            },
            "nets": {
                net.name: {
                    "pins": [{"ref": ref, "pin": pin} for ref, pin, _ in net.pins],
                    "is_power": net.is_power,
                }
                for net in nets
            }
        }

        json.dump(data, output, indent=2)

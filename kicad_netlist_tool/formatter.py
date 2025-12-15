"""Formatters for outputting component and netlist data."""

from typing import Dict, TextIO
from .parser import Component, Net


class CompactFormatter:
    """Formats component and net data in a compact, LLM-friendly format."""
    
    @staticmethod
    def write(components: Dict[str, Component], nets: Dict[str, Net], output: TextIO):
        """Write components and nets in compact format."""
        output.write("# KiCad Netlist Summary\n\n")
        
        # Write components section
        output.write("## Components\n")
        for ref, comp in sorted(components.items()):
            if comp.footprint:
                output.write(f"- {ref}: {comp.value} ({comp.footprint})\n")
            else:
                output.write(f"- {ref}: {comp.value}\n")
        
        output.write("\n")
        
        # Write nets section
        output.write("## Nets\n")
        for net_name, net in sorted(nets.items()):
            if hasattr(net, 'connections') and net.connections:
                connections = ", ".join([f"{ref}.{pin}" for ref, pin in sorted(net.connections)])
                output.write(f"- {net_name}: {connections}\n")
            else:
                output.write(f"- {net_name}: (no connections)\n")
        
        # Write summary
        output.write(f"\n## Summary\n")
        output.write(f"- Components: {len(components)}\n")
        output.write(f"- Nets: {len(nets)}\n")
        total_connections = sum(len(net.connections) if hasattr(net, 'connections') else 0 
                              for net in nets.values())
        output.write(f"- Total connections: {total_connections}\n")


class MarkdownFormatter:
    """Formats component and net data in detailed Markdown tables."""
    
    @staticmethod
    def write(components: Dict[str, Component], nets: Dict[str, Net], output: TextIO):
        """Write components and nets in Markdown table format."""
        output.write("# KiCad Netlist Documentation\n\n")
        
        # Component table
        output.write("## Components\n\n")
        output.write("| Reference | Value | Footprint | Library ID |\n")
        output.write("|-----------|-------|-----------|------------|\n")
        
        for ref, comp in sorted(components.items()):
            output.write(f"| {ref} | {comp.value} | {comp.footprint or 'N/A'} | {comp.lib_id or 'N/A'} |\n")
        
        output.write("\n")
        
        # Net connections table
        output.write("## Net Connections\n\n")
        output.write("| Net Name | Connected Pins |\n")
        output.write("|----------|----------------|\n")
        
        for net_name, net in sorted(nets.items()):
            if net.connections:
                connections = ", ".join([f"{ref}.{pin}" for ref, pin in net.connections])
                output.write(f"| {net_name} | {connections} |\n")


class JsonFormatter:
    """Formats component and net data as JSON."""
    
    @staticmethod
    def write(components: Dict[str, Component], nets: Dict[str, Net], output: TextIO):
        """Write components and nets in JSON format."""
        import json
        
        data = {
            "components": {
                ref: {
                    "value": comp.value,
                    "footprint": comp.footprint,
                    "lib_id": comp.lib_id,
                    "pins": comp.pins
                }
                for ref, comp in components.items()
            },
            "nets": {
                net_name: {
                    "connections": [{"ref": ref, "pin": pin} for ref, pin in net.connections]
                }
                for net_name, net in nets.items()
            }
        }
        
        json.dump(data, output, indent=2)
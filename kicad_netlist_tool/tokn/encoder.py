"""
TOKN encoder - converts KiCad schematics to TOKN format.
"""

import re
from typing import Dict, List, Tuple

from .kicad_sch import (
    Schematic, Component, parse_schematic, parse_hierarchical_schematic,
    HierarchicalSchematic, find_project_root
)
from .connectivity import Netlist, Net, WireSegment, analyze_connectivity


# Type normalization rules
TYPE_NORMALIZATION = {
    'Device:R': 'R',
    'Device:R_Small': 'R',
    'Device:R_US': 'R',
    'Device:R_POT': 'RPOT',
    'Device:C': 'C',
    'Device:C_Small': 'C',
    'Device:C_Polarized': 'CP',
    'Device:C_Polarized_US': 'CP',
    'Device:L': 'L',
    'Device:L_Small': 'L',
    'Device:D': 'D',
    'Device:D_Small': 'D',
    'Device:D_Zener': 'DZ',
    'Device:D_Schottky': 'DS',
    'Device:LED': 'LED',
    'Device:LED_Small': 'LED',
    'Device:Q_NPN_BCE': 'QNPN',
    'Device:Q_NPN_BEC': 'QNPN',
    'Device:Q_NPN_CBE': 'QNPN',
    'Device:Q_NPN_CEB': 'QNPN',
    'Device:Q_NPN_ECB': 'QNPN',
    'Device:Q_NPN_EBC': 'QNPN',
    'Device:Q_PNP_BCE': 'QPNP',
    'Device:Q_PNP_BEC': 'QPNP',
    'Device:Q_PNP_CBE': 'QPNP',
    'Device:Q_PNP_CEB': 'QPNP',
    'Device:Q_PNP_ECB': 'QPNP',
    'Device:Q_PNP_EBC': 'QPNP',
    'Device:Q_NMOS_GDS': 'NMOS',
    'Device:Q_NMOS_GSD': 'NMOS',
    'Device:Q_NMOS_DGS': 'NMOS',
    'Device:Q_NMOS_DSG': 'NMOS',
    'Device:Q_NMOS_SGD': 'NMOS',
    'Device:Q_NMOS_SDG': 'NMOS',
    'Device:Q_PMOS_GDS': 'PMOS',
    'Device:Q_PMOS_GSD': 'PMOS',
    'Device:Q_PMOS_DGS': 'PMOS',
    'Device:Q_PMOS_DSG': 'PMOS',
    'Device:Q_PMOS_SGD': 'PMOS',
    'Device:Q_PMOS_SDG': 'PMOS',
    'Device:Crystal': 'XTAL',
    'Device:Crystal_Small': 'XTAL',
    'Device:Fuse': 'F',
    'Device:Fuse_Small': 'F',
    'Device:Ferrite_Bead': 'FB',
    'Device:Ferrite_Bead_Small': 'FB',
    'Connector:Conn_01x01': 'CONN1',
    'Connector:Conn_01x02': 'CONN2',
    'Connector:Conn_01x03': 'CONN3',
    'Connector:Conn_01x04': 'CONN4',
}

# Footprint shorthand
FOOTPRINT_SHORTHAND = {
    'Resistor_SMD:R_0402_1005Metric': '0402',
    'Resistor_SMD:R_0603_1608Metric': '0603',
    'Resistor_SMD:R_0805_2012Metric': '0805',
    'Resistor_SMD:R_1206_3216Metric': '1206',
    'Capacitor_SMD:C_0402_1005Metric': '0402',
    'Capacitor_SMD:C_0603_1608Metric': '0603',
    'Capacitor_SMD:C_0805_2012Metric': '0805',
    'Capacitor_SMD:C_1206_3216Metric': '1206',
}


def normalize_type(lib_id: str) -> str:
    """Normalize a lib_id to a short type code."""
    # Check direct mapping
    if lib_id in TYPE_NORMALIZATION:
        return TYPE_NORMALIZATION[lib_id]

    # For ICs, extract the part number
    if ':' in lib_id:
        library, part = lib_id.split(':', 1)
        # Skip power symbols
        if library == 'power':
            return part

        # For specific ICs, use the part name
        # Strip common suffixes like package variants
        part = re.sub(r'[-_](I|E|P)[-_]?(SN|SO|P|N|AU|PU)?$', '', part)
        return part

    return lib_id


def normalize_footprint(footprint: str) -> str:
    """Normalize a footprint to shorthand."""
    if not footprint:
        return ''

    # Check direct mapping
    if footprint in FOOTPRINT_SHORTHAND:
        return FOOTPRINT_SHORTHAND[footprint]

    # Extract the last part of the path
    if ':' in footprint:
        footprint = footprint.split(':')[-1]

    # IPC-7351 format: SOIC127P1030X265-20N -> SOIC-20
    # Pattern: PKG + pitch(3 digits) + P + dimensions + -PINS + suffix
    ipc_match = re.match(r'(SOIC|TSSOP|SSOP|QFP|LQFP|TQFP|QFN|DFN|BGA)\d{2,3}P.*-(\d+)[A-Z]?$', footprint)
    if ipc_match:
        pkg = ipc_match.group(1)
        pins = ipc_match.group(2)
        return f"{pkg}-{pins}"

    # KiCad format: SOIC-8_3.9x4.9mm_P1.27mm -> SOIC-8
    kicad_match = re.match(r'(SOIC|TSSOP|SSOP|QFP|LQFP|TQFP|BGA|QFN|DFN|TO-\d+)[-_](\d+)', footprint)
    if kicad_match:
        pkg = kicad_match.group(1)
        pins = kicad_match.group(2)
        return f"{pkg}-{pins}"

    return footprint


def needs_quoting(value: str) -> bool:
    """Check if a value needs to be quoted in TOON format."""
    if not value:
        return False
    # Quote if contains comma, quote, backslash, or is reserved word
    if ',' in value or '"' in value or '\\' in value:
        return True
    if value.lower() in ('true', 'false', 'null'):
        return True
    # Quote if looks like a number but isn't meant to be
    if re.match(r'^-?\d+\.?\d*$', value):
        return False  # Actual numbers don't need quoting
    return False


def quote_value(value: str) -> str:
    """Quote a value if necessary."""
    if needs_quoting(value):
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return value


def encode_tokn(sch: Schematic, netlist: Netlist) -> str:
    """Encode a schematic as TOKN format (flat/merged)."""
    lines = ['# TOKN v1']

    if sch.title:
        lines.append(f'title: {sch.title}')

    lines.append('')

    # Components section
    # Sort components by reference
    components = sorted(netlist.components, key=lambda c: (
        c.reference[0] if c.reference else '',
        int(re.search(r'\d+', c.reference).group()) if re.search(r'\d+', c.reference) else 0
    ))

    if components:
        lines.append(f'components[{len(components)}]{{ref,type,value,fp,x,y,w,h,a}}:')
        for comp in components:
            ref = comp.reference
            comp_type = normalize_type(comp.lib_id)
            value = comp.value or ''
            fp = normalize_footprint(comp.footprint)
            angle = comp.angle  # Rotation angle in degrees

            # Calculate center and size from pin positions (more accurate than component origin)
            if comp.pins:
                pin_xs = [p.x for p in comp.pins.values()]
                pin_ys = [p.y for p in comp.pins.values()]
                # Use pin bounding box center as component center
                x = (min(pin_xs) + max(pin_xs)) / 2
                y = (min(pin_ys) + max(pin_ys)) / 2
                w = max(pin_xs) - min(pin_xs)
                h = max(pin_ys) - min(pin_ys)
            else:
                x = comp.x
                y = comp.y
                w, h = 0, 0

            # Quote values if needed
            value = quote_value(value)
            fp = quote_value(fp)

            lines.append(f'  {ref},{comp_type},{value},{fp},{x:.2f},{y:.2f},{w:.2f},{h:.2f},{angle:.0f}')

    lines.append('')

    # Pins section - list pin definitions for ICs (components with meaningful pin names)
    # Skip simple passives (R, C, L, D, etc.) where pin names aren't informative
    passive_types = {'R', 'C', 'CP', 'L', 'D', 'DZ', 'DS', 'LED', 'F', 'FB'}

    # Group pins by component reference
    component_pins: Dict[str, List[Tuple[str, str]]] = {}  # ref -> [(num, name), ...]

    for comp in components:
        comp_type = normalize_type(comp.lib_id)
        if comp_type in passive_types:
            continue

        # Get pin info from lib_symbol
        lib_sym = None
        if comp.lib_id in sch.lib_symbols:
            lib_sym = sch.lib_symbols[comp.lib_id]

        if lib_sym:
            pins_for_comp = []
            for pin in lib_sym.pins:
                # Include all pins with names (even power/ground - full datasheet info)
                if pin.name and pin.name != '~':
                    pins_for_comp.append((pin.number, pin.name))

            if pins_for_comp:
                component_pins[comp.reference] = pins_for_comp

    # Output pins grouped by component
    if component_pins:
        # Sort components by reference
        sorted_refs = sorted(component_pins.keys(), key=lambda r: (
            r[0] if r else '',
            int(re.search(r'\d+', r).group()) if re.search(r'\d+', r) else 0
        ))

        for ref in sorted_refs:
            pins_list = component_pins[ref]
            lines.append(f'pins{{{ref}}}[{len(pins_list)}]:')
            for num, name in pins_list:
                lines.append(f'  {num},{quote_value(name)}')

        lines.append('')

    # Nets section
    if netlist.nets:
        lines.append(f'nets[{len(netlist.nets)}]{{name,pins}}:')
        for net in netlist.nets:
            name = quote_value(net.name)
            pins_list = [f"{ref}.{pin_num}" for ref, pin_num, _ in net.pins]
            pins_str = ','.join(pins_list)
            # Quote pins if there are multiple (contains comma)
            if len(pins_list) > 1:
                pins_str = f'"{pins_str}"'

            lines.append(f'  {name},{pins_str}')

    lines.append('')

    # Wires section - collect all wire segments with their net names
    all_wires = []
    for net in netlist.nets:
        for wire in net.wires:
            all_wires.append((net.name, wire))

    if all_wires:
        lines.append(f'wires[{len(all_wires)}]{{net,pts}}:')
        for net_name, wire in all_wires:
            name = quote_value(net_name)
            # Format points as "x1 y1,x2 y2,..."
            pts_str = ','.join(f'{x:.2f} {y:.2f}' for x, y in wire.points)
            lines.append(f'  {name},"{pts_str}"')

    lines.append('')
    return '\n'.join(lines)


def encode_sheet_tokn(sch: Schematic) -> str:
    """Encode a single sheet as TOKN format with full connectivity."""
    lines = []

    # Run connectivity analysis for this sheet
    netlist = analyze_connectivity(sch)

    # Components section
    components = sorted(netlist.components, key=lambda c: (
        c.reference[0] if c.reference else '',
        int(re.search(r'\d+', c.reference).group()) if re.search(r'\d+', c.reference) else 0
    ))

    if components:
        lines.append(f'components[{len(components)}]{{ref,type,value,fp,x,y,w,h,a}}:')
        for comp in components:
            ref = comp.reference
            comp_type = normalize_type(comp.lib_id)
            value = comp.value or ''
            fp = normalize_footprint(comp.footprint)
            angle = comp.angle

            if comp.pins:
                pin_xs = [p.x for p in comp.pins.values()]
                pin_ys = [p.y for p in comp.pins.values()]
                x = (min(pin_xs) + max(pin_xs)) / 2
                y = (min(pin_ys) + max(pin_ys)) / 2
                w = max(pin_xs) - min(pin_xs)
                h = max(pin_ys) - min(pin_ys)
            else:
                x = comp.x
                y = comp.y
                w, h = 0, 0

            value = quote_value(value)
            fp = quote_value(fp)

            lines.append(f'  {ref},{comp_type},{value},{fp},{x:.2f},{y:.2f},{w:.2f},{h:.2f},{angle:.0f}')

        lines.append('')

    # Pins section - list pin definitions for ICs
    passive_types = {'R', 'C', 'CP', 'L', 'D', 'DZ', 'DS', 'LED', 'F', 'FB'}
    component_pins: Dict[str, List[Tuple[str, str]]] = {}

    for comp in components:
        comp_type = normalize_type(comp.lib_id)
        if comp_type in passive_types:
            continue

        lib_sym = None
        if comp.lib_id in sch.lib_symbols:
            lib_sym = sch.lib_symbols[comp.lib_id]

        if lib_sym:
            pins_for_comp = []
            for pin in lib_sym.pins:
                if pin.name and pin.name != '~':
                    pins_for_comp.append((pin.number, pin.name))

            if pins_for_comp:
                component_pins[comp.reference] = pins_for_comp

    if component_pins:
        sorted_refs = sorted(component_pins.keys(), key=lambda r: (
            r[0] if r else '',
            int(re.search(r'\d+', r).group()) if re.search(r'\d+', r) else 0
        ))

        for ref in sorted_refs:
            pins_list = component_pins[ref]
            lines.append(f'pins{{{ref}}}[{len(pins_list)}]:')
            for num, name in pins_list:
                lines.append(f'  {num},{quote_value(name)}')

        lines.append('')

    # Nets section
    if netlist.nets:
        lines.append(f'nets[{len(netlist.nets)}]{{name,pins}}:')
        for net in netlist.nets:
            name = quote_value(net.name)
            pins_list = [f"{ref}.{pin_num}" for ref, pin_num, _ in net.pins]
            pins_str = ','.join(pins_list)
            if len(pins_list) > 1:
                pins_str = f'"{pins_str}"'

            lines.append(f'  {name},{pins_str}')

        lines.append('')

    # Wires section
    all_wires = []
    for net in netlist.nets:
        for wire in net.wires:
            all_wires.append((net.name, wire))

    if all_wires:
        lines.append(f'wires[{len(all_wires)}]{{net,pts}}:')
        for net_name, wire in all_wires:
            name = quote_value(net_name)
            pts_str = ','.join(f'{x:.2f} {y:.2f}' for x, y in wire.points)
            lines.append(f'  {name},"{pts_str}"')

    return '\n'.join(lines)


def encode_hierarchical_tokn(hier: HierarchicalSchematic) -> str:
    """Encode a hierarchical schematic as TOKN format with per-sheet sections."""
    lines = ['# TOKN v1']
    lines.append(f'project: {hier.project_name}')
    lines.append(f'root: {hier.root_file}')
    lines.append(f'sheets: {len(hier.sheets)}')

    # Calculate total components
    total_components = sum(len(sch.components) for _, sch in hier.sheets)
    lines.append(f'total_components: {total_components}')
    lines.append('')

    # Output each sheet
    for hier_path, sch in hier.sheets:
        lines.append(f'# sheet: {hier_path}')
        lines.append(f'# file: {sch.filename}')
        if sch.title:
            lines.append(f'# title: {sch.title}')
        lines.append('')

        # Encode this sheet's components
        sheet_tokn = encode_sheet_tokn(sch)
        if sheet_tokn:
            lines.append(sheet_tokn)
        else:
            lines.append('# (no components)')
        lines.append('')

    return '\n'.join(lines)


def convert_file(input_path: str, output_path: str = None, hierarchical: bool = True) -> str:
    """Convert a KiCad schematic file to TOKN format.

    Args:
        input_path: Path to .kicad_sch file
        output_path: Optional output file path
        hierarchical: If True, output hierarchical format with per-sheet sections

    Returns:
        TOKN formatted string
    """
    if hierarchical:
        hier = parse_hierarchical_schematic(input_path)
        tokn = encode_hierarchical_tokn(hier)
    else:
        sch = parse_schematic(input_path)
        netlist = analyze_connectivity(sch)
        tokn = encode_tokn(sch, netlist)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tokn)
        print(f"Written to {output_path}")

    return tokn


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tokn_encoder.py <schematic.kicad_sch> [output.tokn]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    tokn = convert_file(input_file, output_file)

    if not output_file:
        print(tokn)

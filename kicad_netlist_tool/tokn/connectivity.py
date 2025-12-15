"""
Connectivity analyzer for KiCad schematics.

Builds a net list by tracing wire connections between component pins.
"""

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional, List, Dict, Set, Tuple

from .kicad_sch import Schematic, Component, Wire, Junction, Label, Point


@dataclass
class WireSegment:
    """A wire segment with its points."""
    points: List[Tuple[float, float]]  # List of (x, y) coordinates


@dataclass
class Net:
    """A net connecting multiple pins."""
    name: str
    pins: List[Tuple[str, str, str]] = field(default_factory=list)  # (ref, pin_number, pin_name)
    wires: List[WireSegment] = field(default_factory=list)  # Wire segments in this net
    is_power: bool = False


@dataclass
class Netlist:
    """Complete netlist extracted from a schematic."""
    nets: List[Net] = field(default_factory=list)
    components: List[Component] = field(default_factory=list)


def analyze_connectivity(sch: Schematic, tolerance: float = 0.01) -> Netlist:
    """
    Analyze schematic connectivity and build a netlist.

    Algorithm:
    1. Build a graph of all wire segments and junction points
    2. Find connected components in this graph (each is a potential net)
    3. For each connected component, find all pins that touch it
    4. Assign net names from labels or generate anonymous names
    """
    # Build point-to-segment mapping
    # Each point can connect to multiple wire segments
    point_to_segments: Dict[Point, List[int]] = defaultdict(list)

    for i, wire in enumerate(sch.wires):
        for pt in wire.points:
            point_to_segments[pt].append(i)

    # Add junctions as explicit connection points
    junction_points = {Point(j.x, j.y) for j in sch.junctions}

    # Build adjacency: which segments connect to which
    segment_adj: Dict[int, Set[int]] = defaultdict(set)

    for pt, segments in point_to_segments.items():
        # All segments sharing this point are connected
        for i in segments:
            for j in segments:
                if i != j:
                    segment_adj[i].add(j)

    # Also connect segments that share endpoints (wires can chain)
    for i, wire_i in enumerate(sch.wires):
        for j, wire_j in enumerate(sch.wires):
            if i >= j:
                continue
            # Check if any endpoint of wire_i matches any endpoint of wire_j
            for pt_i in wire_i.points:
                for pt_j in wire_j.points:
                    if points_match(pt_i, pt_j, tolerance):
                        segment_adj[i].add(j)
                        segment_adj[j].add(i)

    # Find connected components of wire segments using union-find
    parent = list(range(len(sch.wires)))

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i, neighbors in segment_adj.items():
        for j in neighbors:
            union(i, j)

    # Group segments by their root
    segment_groups: Dict[int, List[int]] = defaultdict(list)
    for i in range(len(sch.wires)):
        segment_groups[find(i)].append(i)

    # For each group, collect all points
    group_points: Dict[int, Set[Point]] = {}
    for root, segments in segment_groups.items():
        pts = set()
        for seg_idx in segments:
            for pt in sch.wires[seg_idx].points:
                pts.add(pt)
        group_points[root] = pts

    # Build pin position to (ref, pin_number, pin_name) mapping
    pin_positions: Dict[Point, List[Tuple[str, str, str]]] = defaultdict(list)
    for comp in sch.components:
        # Look up pin names from lib_symbol
        lib_sym = sch.lib_symbols.get(comp.lib_id)
        pin_names = {}
        if lib_sym:
            for pin in lib_sym.pins:
                pin_names[pin.number] = pin.name

        for pin_num, pin_pos in comp.pins.items():
            pin_name = pin_names.get(pin_num, '')
            pin_positions[pin_pos].append((comp.reference, pin_num, pin_name))

    # Build label position to label name mapping
    label_positions: Dict[Point, str] = {}
    for label in sch.labels:
        label_positions[Point(label.x, label.y)] = label.name

    # For each wire group, find connected pins and labels
    nets: List[Net] = []
    anonymous_counter = 1

    for root, points in group_points.items():
        pins: List[Tuple[str, str, str]] = []
        net_name: Optional[str] = None
        is_power = False

        for pt in points:
            # Check for pins at this point (with tolerance)
            for pin_pt, pin_list in pin_positions.items():
                if points_match(pt, pin_pt, tolerance):
                    pins.extend(pin_list)

            # Check for labels at this point
            for label_pt, label_name in label_positions.items():
                if points_match(pt, label_pt, tolerance):
                    net_name = label_name

        # Check if any connected pin is a power symbol
        for ref, pin_num, pin_name in pins:
            comp = next((c for c in sch.components if c.reference == ref), None)
            if comp and comp.lib_id in sch.lib_symbols:
                if sch.lib_symbols[comp.lib_id].is_power:
                    # Use the value as the net name (e.g., "+5V", "GND")
                    net_name = comp.value
                    is_power = True
                    break

        # Remove power symbol pins from the pin list (they define nets, not connections)
        pins = [(ref, pin_num, pin_name) for ref, pin_num, pin_name in pins
                if not (any(c.reference == ref and c.lib_id in sch.lib_symbols and
                          sch.lib_symbols[c.lib_id].is_power
                          for c in sch.components))]

        # Skip empty nets
        if not pins:
            continue

        # Assign anonymous name if needed
        if net_name is None:
            net_name = f"N{anonymous_counter}"
            anonymous_counter += 1

        # Remove duplicates while preserving order
        seen = set()
        unique_pins = []
        for pin in pins:
            if pin not in seen:
                seen.add(pin)
                unique_pins.append(pin)

        # Collect wire segments for this net
        wire_segments = []
        for seg_idx in segment_groups[root]:
            wire = sch.wires[seg_idx]
            segment_points = [(p.x, p.y) for p in wire.points]
            wire_segments.append(WireSegment(points=segment_points))

        nets.append(Net(name=net_name, pins=unique_pins, wires=wire_segments, is_power=is_power))

    # Filter out components that are power symbols
    real_components = [c for c in sch.components
                       if not (c.lib_id in sch.lib_symbols and
                              sch.lib_symbols[c.lib_id].is_power)]

    # Merge nets with the same name
    merged_nets: Dict[str, Net] = {}
    for net in nets:
        if net.name in merged_nets:
            # Merge pins and wires into existing net
            existing = merged_nets[net.name]
            for pin in net.pins:
                if pin not in existing.pins:
                    existing.pins.append(pin)
            existing.wires.extend(net.wires)
            existing.is_power = existing.is_power or net.is_power
        else:
            merged_nets[net.name] = net
    nets = list(merged_nets.values())

    # Sort nets: power first, then named, then anonymous
    def net_sort_key(net: Net):
        name = net.name
        if net.is_power:
            # Power nets first, sorted by voltage (descending for positive, ascending for negative)
            if name.startswith('+'):
                try:
                    voltage = float(''.join(c for c in name if c.isdigit() or c == '.'))
                    return (0, -voltage, name)
                except:
                    return (0, 0, name)
            elif name == 'GND' or name.startswith('GND'):
                return (1, 0, name)
            elif name.startswith('-'):
                try:
                    voltage = float(''.join(c for c in name if c.isdigit() or c == '.'))
                    return (2, voltage, name)
                except:
                    return (2, 0, name)
            else:
                return (0, 0, name)
        elif name.startswith('N') and name[1:].isdigit():
            # Anonymous nets last
            return (4, int(name[1:]), name)
        else:
            # Named nets in between
            return (3, 0, name)

    nets.sort(key=net_sort_key)

    # Sort pins within each net
    for net in nets:
        net.pins.sort(key=lambda p: (p[0], int(p[1]) if p[1].isdigit() else 0, p[2]))

    return Netlist(nets=nets, components=real_components)


def points_match(p1: Point, p2: Point, tolerance: float = 0.01) -> bool:
    """Check if two points are within tolerance of each other."""
    return abs(p1.x - p2.x) < tolerance and abs(p1.y - p2.y) < tolerance


def print_netlist(netlist: Netlist):
    """Print the netlist in a readable format."""
    print("Components:")
    for comp in netlist.components:
        print(f"  {comp.reference}: {comp.lib_id} = {comp.value}")

    print("\nNets:")
    for net in netlist.nets:
        pins_str = ", ".join(f"{ref}.{pin_num}:{pin_name}" if pin_name else f"{ref}.{pin_num}"
                             for ref, pin_num, pin_name in net.pins)
        power_marker = " [POWER]" if net.is_power else ""
        print(f"  {net.name}: {pins_str}{power_marker}")


if __name__ == '__main__':
    import sys
    from .kicad_sch import parse_schematic

    if len(sys.argv) < 2:
        print("Usage: python connectivity.py <schematic.kicad_sch>")
        sys.exit(1)

    sch = parse_schematic(sys.argv[1])
    print(f"Analyzing: {sch.title}\n")

    netlist = analyze_connectivity(sch)
    print_netlist(netlist)

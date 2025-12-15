"""Enhanced parser for KiCad schematic files with proper net extraction."""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import sexpdata
from dataclasses import dataclass, field
from collections import defaultdict
import math


@dataclass
class Pin:
    """Represents a pin on a component."""
    number: str
    name: str
    type: str  # input, output, passive, power_in, etc.
    position: Tuple[float, float]  # relative to component origin
    orientation: int  # 0, 90, 180, 270 degrees


@dataclass  
class LibSymbol:
    """Represents a symbol definition from the library."""
    lib_id: str
    pins: Dict[str, Pin] = field(default_factory=dict)  # pin_number -> Pin
    units: Dict[int, List[str]] = field(default_factory=dict)  # unit -> list of pin numbers


@dataclass
class Component:
    """Represents a component instance in the schematic."""
    reference: str
    value: str
    footprint: str = ""
    lib_id: str = ""
    unit: int = 1
    uuid: str = ""
    position: Tuple[float, float] = (0, 0)
    rotation: float = 0.0
    mirror: bool = False
    lib_symbol: Optional[LibSymbol] = None


@dataclass
class Wire:
    """Represents a wire segment."""
    start: Tuple[float, float]
    end: Tuple[float, float]
    uuid: str = ""


@dataclass
class Junction:
    """Represents a junction (connection point)."""
    position: Tuple[float, float]
    uuid: str = ""


@dataclass
class Label:
    """Represents a net label."""
    text: str
    position: Tuple[float, float]
    uuid: str = ""
    is_global: bool = False


@dataclass
class Net:
    """Represents an electrical net."""
    name: str
    connections: Set[Tuple[str, str]] = field(default_factory=set)  # (reference, pin)
    positions: Set[Tuple[float, float]] = field(default_factory=set)  # connected positions


class EnhancedKiCadParser:
    """Enhanced parser that properly extracts nets from KiCad schematics."""
    
    def __init__(self):
        self.lib_symbols: Dict[str, LibSymbol] = {}
        self.components: Dict[str, Component] = {}
        self.wires: List[Wire] = []
        self.junctions: List[Junction] = []
        self.labels: List[Label] = []
        self.nets: Dict[str, Net] = {}
        
    def parse_file(self, filepath: Path) -> Tuple[Dict[str, Component], Dict[str, Net]]:
        """Parse a KiCad schematic file and extract components and nets."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse S-expression
        data = sexpdata.loads(content)
        
        # Process in order:
        # 1. Library symbols (to get pin definitions)
        # 2. Components (symbol instances)
        # 3. Wires, junctions, and labels
        # 4. Build nets from connectivity
        
        self._process_schematic(data)
        self._build_nets()
        
        return self.components, self.nets
    
    def _process_schematic(self, data):
        """Process the schematic data in the correct order."""
        if not isinstance(data, list) or data[0] != sexpdata.Symbol('kicad_sch'):
            raise ValueError("Not a valid KiCad schematic file")
        
        # First pass: extract library symbols
        for item in data[1:]:
            if isinstance(item, list) and item[0] == sexpdata.Symbol('lib_symbols'):
                self._process_lib_symbols(item)
                break
        
        # Second pass: extract everything else
        for item in data[1:]:
            if not isinstance(item, list) or len(item) == 0:
                continue
                
            item_type = item[0]
            
            if item_type == sexpdata.Symbol('symbol'):
                self._process_symbol_instance(item)
            elif item_type == sexpdata.Symbol('wire'):
                self._process_wire(item)
            elif item_type == sexpdata.Symbol('junction'):
                self._process_junction(item)
            elif item_type == sexpdata.Symbol('label'):
                self._process_label(item, is_global=False)
            elif item_type == sexpdata.Symbol('global_label'):
                self._process_label(item, is_global=True)
    
    def _process_lib_symbols(self, lib_symbols_data):
        """Process library symbol definitions."""
        for item in lib_symbols_data[1:]:
            if isinstance(item, list) and item[0] == sexpdata.Symbol('symbol'):
                self._process_lib_symbol(item)
    
    def _process_lib_symbol(self, symbol_data):
        """Process a library symbol definition."""
        lib_id = str(symbol_data[1]).strip('"')
        lib_symbol = LibSymbol(lib_id)
        
        # Process symbol units to find pins
        for item in symbol_data[2:]:
            if not isinstance(item, list):
                continue
                
            if item[0] == sexpdata.Symbol('symbol') and len(item) > 1:
                # This is a symbol unit definition
                unit_name = str(item[1]).strip('"')
                
                # Extract unit number from name (e.g., "C_1_1" -> unit 1)
                parts = unit_name.split('_')
                if len(parts) >= 3 and parts[-2].isdigit():
                    unit_num = int(parts[-2])
                else:
                    unit_num = 1
                
                # Process pins in this unit
                for subitem in item[2:]:
                    if isinstance(subitem, list) and subitem[0] == sexpdata.Symbol('pin'):
                        pin = self._process_lib_pin(subitem)
                        if pin:
                            lib_symbol.pins[pin.number] = pin
                            if unit_num not in lib_symbol.units:
                                lib_symbol.units[unit_num] = []
                            lib_symbol.units[unit_num].append(pin.number)
        
        self.lib_symbols[lib_id] = lib_symbol
    
    def _process_lib_pin(self, pin_data):
        """Process a pin definition from a library symbol."""
        pin_type = str(pin_data[1]) if len(pin_data) > 1 else "passive"
        pin_style = str(pin_data[2]) if len(pin_data) > 2 else "line"
        
        pin = Pin("", "", pin_type, (0, 0), 0)
        
        for item in pin_data[3:]:
            if not isinstance(item, list):
                continue
                
            if item[0] == sexpdata.Symbol('at'):
                pin.position = (float(item[1]), float(item[2]))
                pin.orientation = int(item[3]) if len(item) > 3 else 0
            elif item[0] == sexpdata.Symbol('length'):
                pass  # We might need this for accurate positioning
            elif item[0] == sexpdata.Symbol('name'):
                pin.name = str(item[1]).strip('"')
            elif item[0] == sexpdata.Symbol('number'):
                pin.number = str(item[1]).strip('"')
        
        return pin if pin.number else None
    
    def _process_symbol_instance(self, symbol_data):
        """Process a symbol instance (component)."""
        component = Component("", "")
        
        # Extract basic properties
        for item in symbol_data[1:]:
            if not isinstance(item, list):
                continue
                
            if item[0] == sexpdata.Symbol('lib_id'):
                component.lib_id = str(item[1]).strip('"')
            elif item[0] == sexpdata.Symbol('at'):
                component.position = (float(item[1]), float(item[2]))
                component.rotation = float(item[3]) if len(item) > 3 else 0
            elif item[0] == sexpdata.Symbol('mirror'):
                component.mirror = str(item[1]) == 'y'
            elif item[0] == sexpdata.Symbol('unit'):
                component.unit = int(item[1])
            elif item[0] == sexpdata.Symbol('uuid'):
                component.uuid = str(item[1]).strip('"')
            elif item[0] == sexpdata.Symbol('property'):
                prop_name = str(item[1]).strip('"')
                prop_value = str(item[2]).strip('"') if len(item) > 2 else ""
                
                if prop_name == "Reference":
                    component.reference = prop_value
                elif prop_name == "Value":
                    component.value = prop_value
                elif prop_name == "Footprint":
                    component.footprint = prop_value
        
        # Link to library symbol
        if component.lib_id in self.lib_symbols:
            component.lib_symbol = self.lib_symbols[component.lib_id]
        
        if component.reference:
            self.components[component.reference] = component
    
    def _process_wire(self, wire_data):
        """Process a wire connection."""
        points = []
        uuid = ""
        
        for item in wire_data[1:]:
            if not isinstance(item, list):
                continue
                
            if item[0] == sexpdata.Symbol('pts'):
                for pt in item[1:]:
                    if isinstance(pt, list) and pt[0] == sexpdata.Symbol('xy'):
                        points.append((float(pt[1]), float(pt[2])))
            elif item[0] == sexpdata.Symbol('uuid'):
                uuid = str(item[1]).strip('"')
        
        if len(points) >= 2:
            wire = Wire(points[0], points[1], uuid)
            self.wires.append(wire)
    
    def _process_junction(self, junction_data):
        """Process a junction."""
        pos = None
        uuid = ""
        
        for item in junction_data[1:]:
            if not isinstance(item, list):
                continue
                
            if item[0] == sexpdata.Symbol('at'):
                pos = (float(item[1]), float(item[2]))
            elif item[0] == sexpdata.Symbol('uuid'):
                uuid = str(item[1]).strip('"')
        
        if pos:
            junction = Junction(pos, uuid)
            self.junctions.append(junction)
    
    def _process_label(self, label_data, is_global=False):
        """Process a label."""
        text = ""
        pos = None
        uuid = ""
        
        for item in label_data[1:]:
            if isinstance(item, str):
                text = item.strip('"')
            elif isinstance(item, list):
                if item[0] == sexpdata.Symbol('at'):
                    pos = (float(item[1]), float(item[2]))
                elif item[0] == sexpdata.Symbol('uuid'):
                    uuid = str(item[1]).strip('"')
        
        if text and pos:
            label = Label(text, pos, uuid, is_global)
            self.labels.append(label)
    
    def _get_pin_position(self, component: Component, pin: Pin) -> Tuple[float, float]:
        """Calculate the absolute position of a pin on a component."""
        # Start with pin's relative position
        px, py = pin.position
        
        # Apply component rotation
        angle_rad = math.radians(component.rotation)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Rotate pin position
        rotated_x = px * cos_a - py * sin_a
        rotated_y = px * sin_a + py * cos_a
        
        # Apply mirror if needed
        if component.mirror:
            rotated_x = -rotated_x
        
        # Translate to component position
        abs_x = component.position[0] + rotated_x
        abs_y = component.position[1] + rotated_y
        
        return (abs_x, abs_y)
    
    def _points_connected(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                         tolerance: float = 0.01) -> bool:
        """Check if two points are connected (within tolerance)."""
        return abs(p1[0] - p2[0]) < tolerance and abs(p1[1] - p2[1]) < tolerance
    
    def _build_nets(self):
        """Build nets by tracing wire connections."""
        # Create a graph of connected points
        connections = defaultdict(set)
        
        # Add wire connections
        for wire in self.wires:
            connections[wire.start].add(wire.end)
            connections[wire.end].add(wire.start)
        
        # Add junction connections (all wires meeting at a junction are connected)
        for junction in self.junctions:
            junction_pos = junction.position
            connected_points = set()
            
            # Find all wire endpoints at this junction
            for wire in self.wires:
                if self._points_connected(wire.start, junction_pos):
                    connected_points.add(wire.start)
                if self._points_connected(wire.end, junction_pos):
                    connected_points.add(wire.end)
            
            # Connect all points at this junction
            for p1 in connected_points:
                for p2 in connected_points:
                    if p1 != p2:
                        connections[p1].add(p2)
        
        # Find connected groups (nets) using DFS
        visited = set()
        net_groups = []
        
        def dfs(point, group):
            if point in visited:
                return
            visited.add(point)
            group.add(point)
            for neighbor in connections[point]:
                dfs(neighbor, group)
        
        for point in connections:
            if point not in visited:
                group = set()
                dfs(point, group)
                net_groups.append(group)
        
        # Assign names to nets based on labels
        for i, group in enumerate(net_groups):
            net_name = f"Net_{i+1}"  # Default name
            
            # Check if any label is on this net
            for label in self.labels:
                if any(self._points_connected(label.position, point, tolerance=2.0) 
                       for point in group):
                    net_name = label.text
                    break
            
            # Create net
            net = Net(net_name)
            net.positions = group
            
            # Find component pins connected to this net
            for ref, component in self.components.items():
                if component.lib_symbol:
                    for pin_num, pin in component.lib_symbol.pins.items():
                        # Check if this pin is in the current unit
                        if component.unit in component.lib_symbol.units:
                            if pin_num not in component.lib_symbol.units[component.unit]:
                                continue
                        
                        pin_pos = self._get_pin_position(component, pin)
                        
                        # Check if pin connects to any point in this net
                        for net_point in group:
                            if self._points_connected(pin_pos, net_point, tolerance=2.0):
                                net.connections.add((ref, pin_num))
                                break
            
            if net.connections or net_name != f"Net_{i+1}":  # Keep named nets even if no connections found
                self.nets[net_name] = net
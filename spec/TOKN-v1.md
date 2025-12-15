# TOKN v1 Specification

**Token-Optimised KiCad Notation**

Version: 1.2
Date: 2025-12-06

## 1. Overview

TOKN is a compact textual representation of KiCad schematic files (`.kicad_sch`) optimised for LLM training and generation. It preserves electrical connectivity and visual layout while stripping redundant metadata, achieving 90%+ token reduction.

TOKN is built on [TOON](https://github.com/toon-format/spec) (Token-Oriented Object Notation) and inherits its syntax rules.

### 1.1 Design Goals

1. **Minimal tokens** — strip UUIDs, graphics, redundant metadata
2. **Preserve electrical intent** — component types, values, connectivity
3. **Preserve layout** — component positions, wire geometry for schematic reconstruction
4. **Lossless round-trip** — `kicad_sch → TOKN → kicad_sch` produces visually similar output
5. **Learnable structure** — consistent patterns for LLM training

### 1.2 Non-Goals

- Full visual fidelity — annotation text, custom symbols may differ
- Custom symbol support — assumes standard KiCad libraries

## 2. File Structure

A TOKN file consists of:

```toon
# TOKN v1
title: <schematic title>

components[N]{ref,type,value,fp,x,y,w,h,a}:
  <component rows>

pins{REF}[N]:
  <pin rows for REF>

nets[N]{name,pins}:
  <net rows>

wires[N]{net,pts}:
  <wire rows>
```

### 2.1 Header

```toon
# TOKN v1
```

Required first line. Identifies format version.

### 2.2 Title (optional)

```toon
title: MCP2551 CAN Transceiver
```

Human-readable schematic name. Omit if not meaningful.

## 3. Components Section

### 3.1 Format

```toon
components[N]{ref,type,value,fp,x,y,w,h,a}:
  R1,R,10k,0805,127.00,85.09,7.62,0.00,90
  U1,MCP2551,MCP2551-I-SN,SOIC-8,149.86,85.09,25.40,20.32,0
  C1,C,100n,,123.19,64.77,0.00,7.62,0
```

### 3.2 Fields

| Field | Required | Description |
|-------|----------|-------------|
| `ref` | Yes | Reference designator (R1, C1, U1) |
| `type` | Yes | Normalised component type (see §4) |
| `value` | Yes | Component value or part number |
| `fp` | No | Footprint shorthand (see §4.3) |
| `x` | Yes | X coordinate (center of pin bounding box) |
| `y` | Yes | Y coordinate (center of pin bounding box) |
| `w` | Yes | Width (horizontal pin spread) |
| `h` | Yes | Height (vertical pin spread) |
| `a` | Yes | Angle in degrees (0, 90, 180, 270) |

### 3.3 Coordinate System

- Origin (0,0) is top-left of schematic
- X increases to the right
- Y increases downward (standard KiCad schematic convention)
- Coordinates are in millimeters
- Component x,y is the center of the pin bounding box (not the KiCad symbol origin)

### 3.4 Component Size (w,h)

Width and height represent the pin spread:
- `w`: horizontal distance between leftmost and rightmost pins
- `h`: vertical distance between topmost and bottommost pins

For 2-pin components:
- Horizontal orientation: w > 0, h ≈ 0
- Vertical orientation: w ≈ 0, h > 0

For ICs: both w and h are typically non-zero.

### 3.5 Rotation (a)

Angle in degrees, typically 0, 90, 180, or 270.
- 0°: default/horizontal orientation
- 90°: rotated 90° clockwise (vertical orientation for 2-pin components)
- 180°: flipped
- 270°: rotated 270° clockwise

### 3.6 Ordering

Components are ordered by reference designator:
1. Alphabetically by prefix (C, D, J, L, Q, R, U, etc.)
2. Numerically within prefix (R1, R2, R10, R11)

### 3.7 Exclusions

The following are NOT listed in components:
- Power symbols (+5V, GND, VCC, etc.) — these define nets, not components
- PWR_FLAG symbols
- No-connect symbols
- Graphical symbols (logos, frames)

## 4. Type Normalisation

### 4.1 Standard Device Types

KiCad `lib_id` values are normalised to short type codes:

| lib_id Pattern | Type | Notes |
|----------------|------|-------|
| `Device:R` | `R` | Resistor |
| `Device:R_Small` | `R` | |
| `Device:R_POT` | `RPOT` | Potentiometer |
| `Device:C` | `C` | Capacitor |
| `Device:C_Small` | `C` | |
| `Device:C_Polarized` | `CP` | Electrolytic/tantalum |
| `Device:L` | `L` | Inductor |
| `Device:D` | `D` | Diode |
| `Device:D_Zener` | `DZ` | Zener diode |
| `Device:D_Schottky` | `DS` | Schottky diode |
| `Device:LED` | `LED` | |
| `Device:Q_NPN_BCE` | `QNPN` | NPN transistor |
| `Device:Q_PNP_BCE` | `QPNP` | PNP transistor |
| `Device:Q_NMOS_GDS` | `NMOS` | N-channel MOSFET |
| `Device:Q_PMOS_GDS` | `PMOS` | P-channel MOSFET |
| `Device:Crystal` | `XTAL` | Crystal oscillator |
| `Device:Fuse` | `F` | Fuse |
| `Device:Ferrite_Bead` | `FB` | Ferrite bead |

### 4.2 Specific ICs

For ICs and specific parts, extract the part number from `lib_id`:

| lib_id | Type |
|--------|------|
| `Interface_CAN_LIN:MCP2551-I-SN` | `MCP2551` |
| `Regulator_Linear:LM7805_TO220` | `LM7805` |
| `Amplifier_Operational:LM358` | `LM358` |
| `MCU_Microchip_ATmega:ATmega328P-AU` | `ATmega328P` |

Rule: Use the primary part number, stripping package suffixes when they appear in the value field.

### 4.3 Footprint Shorthand

Common footprints are abbreviated:

| Full Footprint | Shorthand |
|----------------|-----------|
| `Resistor_SMD:R_0402_1005Metric` | `0402` |
| `Resistor_SMD:R_0603_1608Metric` | `0603` |
| `Resistor_SMD:R_0805_2012Metric` | `0805` |
| `Capacitor_SMD:C_0402_1005Metric` | `0402` |
| `Package_SO:SOIC-8_3.9x4.9mm_P1.27mm` | `SOIC-8` |
| `Package_SO:TSSOP-14_4.4x5mm_P0.65mm` | `TSSOP-14` |
| `Package_QFP:LQFP-48_7x7mm_P0.5mm` | `LQFP-48` |
| `Package_TO_SOT_THT:TO-220-3_Vertical` | `TO-220` |

For unlisted footprints, use the final component of the footprint path.

Omit footprint if not specified in source schematic.

## 4a. Pins Section

### 4a.1 Format

Pins are grouped by component reference to minimize repetition:

```toon
pins{IC19}[20]:
  1,VDD
  2,GND
  3,VREF
  4,OUT
  5,NC_1
  6,NC_2
  7,INT/HOLD
  8,~{CS}
  9,XIN
  10,XOUT
  11,SDO
  12,SDI
  13,SCLK
  14,~{TEST}
  15,CH2P
  16,CH2N
  17,CH2FB
  18,CH1FB
  19,CH1N
  20,CH1P
pins{Y1}[4]:
  1,EN-H/Float
  2,GND
  3,OUTPUT
  4,VDD
```

### 4a.2 Header Format

`pins{REF}[N]:` where:
- `REF` is the component reference designator
- `N` is the total pin count for this component

### 4a.3 Pin Row Format

Each pin row is `num,name` where:
- `num` is the pin number
- `name` is the full datasheet pin name, including alternate functions (e.g., `PC6/~{RESET}`)

### 4a.4 Purpose

The pins section provides complete pin definitions from the symbol library. This enables LLMs to:
- Understand pin functions for all pins, including unconnected ones
- Make correct connections based on alternate pin functions
- Handle multi-function pins (e.g., GPIO with UART/SPI alternates)

### 4a.5 Inclusion Rules

All pins are included for complex components (ICs, crystals, connectors, etc.) where pin names provide semantic value. Pins sections are omitted for:

- Passive components (R, C, L, D) — pin names aren't meaningful
- Pins named `~` (undefined in symbol)

### 4a.6 Ordering

- Components are ordered by reference designator (same rules as §3.6)
- Pins within each component are ordered by pin number (ascending)

## 5. Nets Section

### 5.1 Format

```toon
nets[N]{name,pins}:
  +5V,"U1.3,C1.1,C2.1"
  GND,"U1.2,C1.2,C2.2,R1.2"
  CAN_TX,U1.1
  N1,"R1.1,U1.5"
```

### 5.2 Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Net name |
| `pins` | Yes | Comma-separated list of connected pins |

### 5.3 Pin Notation

Pins are specified as `REF.PIN` where:
- `REF` is the component reference designator
- `PIN` is the pin number (not pin name)

Examples:
- `R1.1` — Pin 1 of R1
- `U1.14` — Pin 14 of U1
- `J1.3` — Pin 3 of connector J1

Pin names are defined separately in the pins section (§4a).

### 5.4 Net Naming

#### Named Nets

Nets with explicit labels in the schematic keep their names:
- Global labels: `CAN_TX`, `SPI_CLK`, `UART_RX`
- Local labels: as written
- Power nets: `+5V`, `+3V3`, `GND`, `VBAT`

#### Anonymous Nets

Nets without labels are assigned sequential names:
- `N1`, `N2`, `N3`, etc.

Anonymous nets are assigned in order of first component reference appearance.

### 5.5 Net Ordering

1. Power nets first, in this order:
   - Positive supplies: `+12V`, `+5V`, `+3V3`, etc. (descending voltage)
   - Ground nets: `GND`, `GNDA`, `GNDPWR`
   - Negative supplies: `-5V`, `-12V`, etc.
2. Named signal nets, alphabetically
3. Anonymous nets, numerically (N1, N2, ...)

### 5.6 Pin Ordering Within Nets

Pins within a net are ordered by:
1. Reference designator (C before R before U)
2. Pin number (ascending)

### 5.7 Single-Pin Nets

Nets with only one pin are typically interface signals (exposed for connection to other sheets or external circuits). They MUST be included:

```toon
nets[3]{name,pins}:
  CAN_TX,U1.1
  CAN_RX,U1.4
  N1,"R1.1,U1.5"
```

## 6. Wires Section

### 6.1 Format

```toon
wires[N]{net,pts}:
  +5V,"128.27 57.15,149.86 57.15"
  +5V,"149.86 57.15,149.86 74.93"
  GND,"123.19 107.95,134.62 107.95"
```

### 6.2 Fields

| Field | Required | Description |
|-------|----------|-------------|
| `net` | Yes | Net name this wire segment belongs to |
| `pts` | Yes | Comma-separated coordinate pairs "x1 y1,x2 y2" |

### 6.3 Wire Segments

Each wire is a straight line segment defined by two or more points:
- Points are space-separated `x y` coordinate pairs
- Multiple points in one row form a polyline
- Coordinates are in millimeters, matching component coordinates

### 6.4 Wire Ordering

Wires are grouped by net, in the same order as the nets section.

### 6.5 Junctions

Junction points (where multiple wires connect) are implicit:
- Wires sharing an endpoint are electrically connected
- No explicit junction markers needed in TOKN

## 7. Encoding Rules

### 7.1 From KiCad to TOKN

1. **Parse** the `.kicad_sch` S-expression
2. **Extract components**:
   - Collect all `symbol` elements (excluding power/PWR_FLAG)
   - Extract: lib_id, reference, value, footprint, angle
   - Calculate pin positions and bounding box center
   - Normalise type from lib_id
3. **Build connectivity graph**:
   - Map component pin positions from lib_symbols
   - Match wire endpoints to pin positions (within tolerance)
   - Merge wires at junction points
   - Assign net names from labels (global_label, label, hierarchical_label)
   - Power symbols create implicit net names
4. **Extract wire geometry**:
   - Group wire segments by net
   - Store original coordinate pairs
5. **Generate TOKN output**:
   - Sort and format components with positions
   - Sort and format nets
   - Format wire segments

### 7.2 Coordinate Calculation

Component center position (x, y) is calculated as:
- Find all pin positions after rotation/mirror transform
- x = (min_pin_x + max_pin_x) / 2
- y = (min_pin_y + max_pin_y) / 2

This ensures the center is accurate regardless of symbol origin placement.

### 7.3 Quoting Rules (TOON)

Values must be quoted if they:
- Contain commas, quotes, or backslashes
- Are empty strings
- Match reserved words (true, false, null)
- Contain leading/trailing whitespace

Examples:
```toon
N1,"R1.1,U1.5"           # Quoted: contains comma
CAN_TX,U1.1              # Unquoted: simple value
+5V,"128.27 57.15,..."   # Wire points always quoted
```

## 8. Decoding Rules

### 8.1 From TOKN to KiCad

1. **Parse** the TOKN document
2. **Look up symbols**:
   - Map type back to lib_id
   - Fetch symbol definition from KiCad standard library
3. **Place components**:
   - Use stored x, y coordinates
   - Apply stored rotation angle
4. **Route wires**:
   - Use stored wire segment coordinates
   - Add junctions where wire endpoints meet
5. **Generate labels**:
   - Place global_label for named signals
   - Power symbols for power nets
6. **Emit `.kicad_sch`**:
   - Generate UUIDs
   - Include lib_symbols cache
   - Write complete S-expression

### 8.2 Type to lib_id Mapping

Decoders must maintain a reverse mapping table. Ambiguous types require context:

| Type | Preferred lib_id |
|------|------------------|
| `R` | `Device:R` |
| `C` | `Device:C` |
| `CP` | `Device:C_Polarized` |
| `LED` | `Device:LED` |

For ICs, the type IS the part number; look up in KiCad library by name search.

### 8.3 Footprint Lookup

Decoders should maintain a footprint lookup table mapping:
- Passive types (R, C, L) → standard SMD footprints based on shorthand (0402, 0603, 0805)
- Package types → full KiCad footprint paths (SOIC-8, TSSOP-14, etc.)
- Specific parts → manufacturer-specific footprints

The reference implementation uses `footprints.json` for extensible lookup without code changes.

### 8.4 Pin Placement

When generating symbols for ICs:
1. Use pin definitions from the `pins{REF}[N]:` section
2. Apply standard dual-inline layout: pins 1-N/2 on left side, N/2+1 to N on right side
3. Pin 1 at top-left, ascending downward; pin N/2+1 at bottom-right, ascending upward
4. Include pin names from TOKN in the generated lib_symbol

## 9. Examples

### 9.1 MCP2551 CAN Transceiver

```toon
# TOKN v1
title: MCP2551 CAN Transciever

components[5]{ref,type,value,fp,x,y,w,h,a}:
  C60,C,30pf,,123.19,101.60,0.00,7.62,0
  C61,C,0.1uf,,128.27,64.77,0.00,7.62,0
  R1,R,1k,,134.62,101.60,0.00,7.62,0
  R2,R,60R,,172.72,85.09,7.62,0.00,90
  U1,MCP2551,MCP2551-I-SN,SOIC-8,149.86,85.09,25.40,20.32,0

pins{U1}[8]:
  1,TXD
  2,VSS
  3,VDD
  4,RXD
  5,Vref
  6,CANL
  7,CANH
  8,Rs

nets[8]{name,pins}:
  +5V,"C61.1,U1.3"
  GND,"C60.2,C61.2,R1.2,U1.2"
  CAN0_HI,"R2.2,U1.7"
  CAN0_LO,"R2.1,U1.6"
  CAN0_RX,U1.4
  CAN0_TX,U1.1
  N1,"C60.1,U1.5"
  N2,"R1.1,U1.8"

wires[25]{net,pts}:
  +5V,"128.27 57.15,149.86 57.15"
  +5V,"149.86 52.07,149.86 57.15"
  +5V,"128.27 60.96,128.27 57.15"
  +5V,"149.86 57.15,149.86 74.93"
  GND,"123.19 107.95,134.62 107.95"
  ...
```

## 10. Validation Rules

A valid TOKN document must:

1. Begin with `# TOKN v1`
2. Have valid TOON syntax
3. Have unique component references
4. Reference only declared components in nets
5. Reference valid pin numbers for each component type
6. Have no duplicate pins across different nets
7. Have wire net names that exist in the nets section

## 11. Version History

### v1.2 (2025-12-06)
- Added pins section for IC pin definitions (§4a)
- Pin names documented separately from nets for all IC pins (including unconnected)
- Nets section uses simple `REF.PIN` format
- Fixed IPC-7351 footprint parsing (e.g., `SOIC127P...-20N` → `SOIC-20`)

### v1.1 (2025-11-29)
- Added component position fields: x, y (center coordinates)
- Added component size fields: w, h (pin spread)
- Added component rotation field: a (angle in degrees)
- Added wires section for wire geometry preservation
- Changed coordinate calculation to use pin bounding box center

### v1.0-draft (2025-11-29)
- Initial specification

## Appendix A: Reserved Net Names

These net names have special meaning and should match KiCad power symbols:

```
+1V2, +1V8, +2V5, +3V3, +5V, +9V, +12V, +15V, +24V, +48V
-5V, -12V, -15V
GND, GNDA, GNDD, GNDPWR, GNDREF
VCC, VDD, VSS, VEE
VBUS, VBAT
```

## Appendix B: Reference Designator Prefixes

Standard prefixes and their meanings:

| Prefix | Component Type |
|--------|----------------|
| C | Capacitor |
| D | Diode |
| F | Fuse |
| FB | Ferrite bead |
| J | Connector |
| K | Relay |
| L | Inductor |
| LED | Light-emitting diode |
| Q | Transistor |
| R | Resistor |
| RN | Resistor network |
| SW | Switch |
| T | Transformer |
| U | Integrated circuit |
| X, Y | Crystal/oscillator |

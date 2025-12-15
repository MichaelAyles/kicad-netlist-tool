# KiCad Netlist Tool

*Making KiCad schematics LLM-friendly*

---

## The Problem

I wanted to use Claude to help document my circuits. Describe what each block does, generate a BOM, review the design. Simple stuff.

The problem: KiCad schematic files are massive. A modest circuit is 55KB and 25,000+ tokens. At Claude Opus rates, that's $0.50 per query just to read the schematic. Do that a few times during a design session and you've spent more on API calls than on the actual components.

Most of those tokens are noise — UUIDs, coordinates, symbol graphics, metadata. The actual electrical information is maybe 2% of the file.

---

## The Solution

The KiCad Netlist Tool extracts just the electrical information and outputs it in TOKN format — a token-optimised notation designed for LLM consumption:

```
Original: 1,509,037 tokens → TOKN: 51,443 tokens
Reduction: 96.6%
```

That $0.50 query becomes pocket change. Now I can iterate.

![KiCad Netlist Tool](../assets/screenshot.png)

The tool gives you:
- **Hierarchical sheet selection** — pick which sheets to include
- **Copy to clipboard** — paste directly into Claude
- **File monitoring** — auto-regenerate when you save in KiCad
- **Real-time stats** — see exactly how many tokens you're saving

---

## TOKN Format

The output is [TOKN v1.2](/spec/TOKN-v1.md) — a compact format that preserves everything an LLM needs:

```
# TOKN v1
title: Audio Preamp

components[3]{ref,type,value,fp,x,y,w,h,a}:
  U1,ECC83,ECC83-1,Valve,127.00,85.09,25.40,20.32,0
  R1,R,1.5k,0805,149.86,85.09,7.62,0.00,90
  C1,C,10uF,RadialD10,123.19,64.77,0.00,7.62,0

nets[2]{name,pins}:
  VIN,U1.2,C1.1
  VOUT,U1.7,R1.2
```

Components, values, footprints, positions, and net connectivity. Everything electrical, nothing decorative.

---

## What I Actually Use It For

**Documentation**: Paste the netlist into Claude, ask for a functional description of each block. Works well for complex designs where I need to write up what I built.

**Design review**: "Are there any obvious issues with this circuit?" catches missing pull-ups, floating pins, that kind of thing.

**BOM generation**: The component list is already extracted, so generating a formatted BOM is trivial.

**Selective extraction**: Only need to document the power supply section? Just check those sheets and copy. No need to include the whole project.

---

## Tech Stack

- **Language**: Python
- **GUI**: CustomTkinter (modern themed UI with dark mode support)
- **Format**: TOKN v1.2
- **Platforms**: Windows, macOS, Linux

---

**Source Code**: [GitHub](https://github.com/MichaelAyles/kicad-netlist-tool)

#!/usr/bin/env python3
"""GUI launcher for KiCad Netlist Tool."""

import sys
from pathlib import Path

# Add the package to the path
package_dir = Path(__file__).parent.parent
sys.path.insert(0, str(package_dir))

from kicad_netlist_tool.gui.app import main

if __name__ == "__main__":
    main()
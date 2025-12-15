"""Command-line interface for KiCad Netlist Tool."""

import click
from pathlib import Path
import sys
import time
from .tokn import (
    find_project_root,
    parse_hierarchical_schematic,
    encode_hierarchical_tokn,
)


@click.group()
def cli():
    """KiCad Netlist Tool - Extract component and netlist information in TOKN format."""
    pass


@cli.command()
def gui():
    """Launch the GUI interface."""
    from .gui.app import main as gui_main
    gui_main()


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
def parse(path, output):
    """Parse KiCad schematic file(s) and generate TOKN output."""
    path = Path(path)

    # Find root schematic
    if path.is_file() and path.suffix == '.kicad_sch':
        root_sch = path
    elif path.is_dir():
        root_sch, _ = find_project_root(path)
        if not root_sch:
            click.echo(f"No .kicad_sch files found in {path}", err=True)
            sys.exit(1)
    else:
        click.echo(f"Error: {path} is not a .kicad_sch file or directory", err=True)
        sys.exit(1)

    try:
        click.echo(f"Parsing {root_sch}...", err=True)
        hier = parse_hierarchical_schematic(str(root_sch))
        tokn = encode_hierarchical_tokn(hier)

        if output:
            Path(output).write_text(tokn, encoding='utf-8')
            click.echo(f"Output written to {output}", err=True)
        else:
            click.echo(tokn)

    except Exception as e:
        click.echo(f"Error parsing schematic: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), default='netlist.tokn',
              help='Output file (default: netlist.tokn)')
@click.option('--interval', '-i', type=int, default=5,
              help='Update interval in seconds (default: 5)')
def watch(path, output, interval):
    """Watch KiCad project for changes and auto-update netlist."""
    path = Path(path)
    output_path = path / output if path.is_dir() else path.parent / output

    # Find root schematic
    if path.is_file() and path.suffix == '.kicad_sch':
        project_dir = path.parent
    elif path.is_dir():
        project_dir = path
    else:
        click.echo(f"Error: {path} is not a .kicad_sch file or directory", err=True)
        sys.exit(1)

    root_sch, project_name = find_project_root(project_dir)
    if not root_sch:
        click.echo(f"No .kicad_sch files found in {project_dir}", err=True)
        sys.exit(1)

    click.echo(f"Watching {project_dir} for changes...")
    click.echo(f"Project: {project_name}")
    click.echo(f"Output: {output_path}")
    click.echo(f"Interval: {interval}s")
    click.echo("Press Ctrl+C to stop\n")

    # Track file modification times
    mtimes = {}

    def generate():
        """Generate TOKN output."""
        try:
            hier = parse_hierarchical_schematic(str(root_sch))
            tokn = encode_hierarchical_tokn(hier)
            output_path.write_text(tokn, encoding='utf-8')
            sheet_count = len(hier.sheets)
            comp_count = sum(len(s.components) for _, s in hier.sheets)
            click.echo(f"Updated: {sheet_count} sheets, {comp_count} components")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    # Initial generation
    generate()

    try:
        while True:
            changed = False

            for sch_file in project_dir.glob("**/*.kicad_sch"):
                try:
                    mtime = sch_file.stat().st_mtime
                    if sch_file in mtimes and mtimes[sch_file] != mtime:
                        changed = True
                        click.echo(f"Changed: {sch_file.name}")
                    mtimes[sch_file] = mtime
                except (OSError, IOError):
                    pass

            if changed:
                generate()

            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\nStopping watcher...")


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()

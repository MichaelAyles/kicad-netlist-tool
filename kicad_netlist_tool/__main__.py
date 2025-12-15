"""Command-line interface for KiCad Netlist Tool."""

import click
from pathlib import Path
import sys
from .parser import parse_schematic, analyze_connectivity
from .formatter import ToknFormatter, CompactFormatter, MarkdownFormatter, JsonFormatter


@click.group()
def cli():
    """KiCad Netlist Tool - Extract component and netlist information in TOKN format."""
    pass


@cli.command()
def gui():
    """Launch the GUI interface."""
    from .gui.main_window import main as gui_main
    gui_main()


@cli.command()
def tray():
    """Launch the system tray application."""
    from .gui.tray_app import main as tray_main
    tray_main()


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
@click.option('--format', '-f', type=click.Choice(['tokn', 'compact', 'markdown', 'json']),
              default='tokn', help='Output format (default: tokn)')
def parse(path, output, format):
    """Parse KiCad schematic file(s) and extract netlist."""
    path = Path(path)

    # Find schematic files
    if path.is_file() and path.suffix == '.kicad_sch':
        schematic_files = [path]
    elif path.is_dir():
        schematic_files = list(path.glob('*.kicad_sch'))
    else:
        click.echo(f"Error: {path} is not a .kicad_sch file or directory", err=True)
        sys.exit(1)

    if not schematic_files:
        click.echo(f"No .kicad_sch files found in {path}", err=True)
        sys.exit(1)

    # Parse all files and merge results
    all_components = []
    all_nets = []

    for sch_file in schematic_files:
        try:
            click.echo(f"Parsing {sch_file}...", err=True)
            sch = parse_schematic(str(sch_file))
            netlist = analyze_connectivity(sch)
            all_components.extend(netlist.components)
            all_nets.extend(netlist.nets)
        except Exception as e:
            click.echo(f"Error parsing {sch_file}: {e}", err=True)
            sys.exit(1)

    # Output results
    def write_output(out_file):
        if format == 'tokn':
            # For TOKN format, we need the full schematic
            sch = parse_schematic(str(schematic_files[0]))
            netlist = analyze_connectivity(sch)
            ToknFormatter.write(sch, netlist, out_file)
        elif format == 'compact':
            CompactFormatter.write(all_components, all_nets, out_file)
        elif format == 'markdown':
            MarkdownFormatter.write(all_components, all_nets, out_file)
        elif format == 'json':
            JsonFormatter.write(all_components, all_nets, out_file)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            write_output(f)
        click.echo(f"Output written to {output}", err=True)
    else:
        write_output(sys.stdout)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), default='netlist.tokn',
              help='Output file (default: netlist.tokn)')
@click.option('--format', '-f', type=click.Choice(['tokn', 'compact', 'markdown', 'json']),
              default='tokn', help='Output format (default: tokn)')
@click.option('--interval', '-i', type=int, default=30,
              help='Update interval in seconds (default: 30)')
def watch(path, output, format, interval):
    """Watch KiCad project for changes and auto-update netlist."""
    from .watcher import SchematicWatcher

    path = Path(path)
    output_path = Path(output)

    # Create watcher
    watcher = SchematicWatcher(path, output_path, format, interval)

    click.echo(f"Watching {path} for changes...")
    click.echo(f"Output will be written to {output_path}")
    click.echo("Press Ctrl+C to stop")

    try:
        watcher.run()
    except KeyboardInterrupt:
        click.echo("\nStopping watcher...")


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()

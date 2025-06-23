"""Command-line interface for KiCad Netlist Tool."""

import click
from pathlib import Path
import sys
from .parser import KiCadSchematicParser
from .formatter import CompactFormatter, MarkdownFormatter, JsonFormatter
from .watcher import SchematicWatcher


@click.group()
def cli():
    """KiCad Netlist Tool - Extract component and netlist information."""
    pass


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
@click.option('--format', '-f', type=click.Choice(['compact', 'markdown', 'json']), 
              default='compact', help='Output format')
def parse(path, output, format):
    """Parse KiCad schematic file(s) and extract netlist."""
    path = Path(path)
    
    # Determine formatter
    formatters = {
        'compact': CompactFormatter,
        'markdown': MarkdownFormatter,
        'json': JsonFormatter
    }
    formatter = formatters[format]
    
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
    
    # Parse all files
    all_components = {}
    all_nets = {}
    
    parser = KiCadSchematicParser()
    for sch_file in schematic_files:
        try:
            click.echo(f"Parsing {sch_file}...", err=True)
            components, nets = parser.parse_file(sch_file)
            all_components.update(components)
            all_nets.update(nets)
        except Exception as e:
            click.echo(f"Error parsing {sch_file}: {e}", err=True)
            sys.exit(1)
    
    # Output results
    if output:
        with open(output, 'w') as f:
            formatter.write(all_components, all_nets, f)
        click.echo(f"Output written to {output}", err=True)
    else:
        formatter.write(all_components, all_nets, sys.stdout)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), default='netlist.txt',
              help='Output file (default: netlist.txt)')
@click.option('--format', '-f', type=click.Choice(['compact', 'markdown', 'json']), 
              default='compact', help='Output format')
@click.option('--interval', '-i', type=int, default=30,
              help='Update interval in seconds (default: 30)')
def watch(path, output, format, interval):
    """Watch KiCad project for changes and auto-update netlist."""
    path = Path(path)
    output_path = Path(output)
    
    # Determine formatter
    formatters = {
        'compact': CompactFormatter,
        'markdown': MarkdownFormatter,
        'json': JsonFormatter
    }
    formatter = formatters[format]
    
    # Create watcher
    watcher = SchematicWatcher(path, output_path, formatter, interval)
    
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
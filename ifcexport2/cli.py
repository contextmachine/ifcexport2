import multiprocessing
from pathlib import Path
import ujson
import click
from ifcexport2.compat import IfcExportCompat
from ifcexport2.partition import partition_viewer_json

@click.group('ifcexport2')
def ifcexport2_cli():
    ...


@ifcexport2_cli.command(
    name="export",

)
@click.argument(
    "input_file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=Path,
    ),
    metavar="INPUT_FILE",

)
@click.option(
    "-o",
    "--output-prefix",
    type=click.Path(
        file_okay=False,
        dir_okay=False,
        writable=True,
        path_type=Path,
    ),
    default=None,
    show_default="Input filename without extension",
    help=(
            "Prefix for output files. If not specified, the input filename without extension "
            "is used."
    ),
)
@click.option(
    "-f",
    "--output-format",
    type=IfcExportCompat,
    default=IfcExportCompat.viewer,
    show_default=True,
    help=(
            f"Output data format. Can be: {list(IfcExportCompat._value2member_map_.keys())}"
    ),
)
@click.option(
    "-s",
    "--scale",
    type=float,
    default=1.0,
    show_default=True,
    help="Scaling factor to apply to mesh vertices.",
)
@click.option(
    "-e",
    "--exclude",
    multiple=True,
    default=["IfcSpace", "IfcOpeningElement"],
    show_default=True,
    help=(
            "List of IFC types to exclude from processing. "
            "Default excludes 'IfcSpace' and 'IfcOpeningElement'.\n"
            "Example: -e IfcSpace IfcSite IfcOpeningElement"
    ),
)
@click.option(
    "-t",
    "--threads",
    type=int,
    default=multiprocessing.cpu_count(),
    show_default=f"Number of available CPUs: {multiprocessing.cpu_count()}",
    help="Number of CPU threads to use for processing.",
)
@click.option(
    "-p",
    "--print",
    "print_items",
    is_flag=True,
    default=False,
    help="Print progress information during processing.",
)
@click.option(
    "--no-save-fails",
    is_flag=True,
    default=False,
    help="Do not save failed items to the fails JSON file.",
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Outputs the result in a single JSON string. Suitable for scripts.",
)
def export_ifc_to_viewer(input_file: Path,
                         output_prefix: Path,
                         output_format: IfcExportCompat,
                         scale: float,
                         exclude: tuple,
                         threads: int,
                         print_items: bool,
                         no_save_fails: bool,
                         json_output: bool):
    """Process an IFC file to extract geometric meshes and associated data and output in  ifcexport2.cxm-viewer friendly format.

    This script reads an IFC file, extracts geometry data, applies scaling,
    excludes specified types, and outputs meshes with additional properties in three.js json format.
    """

    from ifcexport2 import ifc_to_mesh
    ifc_to_mesh.cli_export(input_file, output_prefix, output_format, scale, exclude, threads, print_items,
                           no_save_fails, json_output)


@ifcexport2_cli.command(
    name="split",
    help="Split a single *.viewer.json file into parts."

)
@click.argument(
    "input_file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=Path,
    ),
    metavar="INPUT_FILE",
)
@click.argument(
    "parts_count",
    type=int,
    metavar="PARTS_COUNT",
)
@click.option(
    "-o",
    "--output-dir",

    type=click.Path(
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=Path,
    ),
    default=Path("."),

    show_default=True,
    help=(
            "Path to the directory where the split files will be written. By default current working directory"))
def split_viewer_json(input_file: Path, parts_count: int, output_dir: Path):
    with input_file.open('r') as f:
        data=ujson.load(f)
        res=partition_viewer_json(data,parts_count)
    _ifl=input_file.name
    for sf in input_file.suffixes:
        _ifl=_ifl.replace(sf,'')

    for part,r in enumerate(res):
        with (output_dir/f'{_ifl}-{part}.viewer.json').open('w')as fl:
            ujson.dump(r, fl,ensure_ascii=False)


if __name__ == "__main__":
    ifcexport2_cli()

from __future__ import annotations

import argparse
import dataclasses

from ifcexport2.mesh_to_three import create_three_js_root, mesh_to_three, add_mesh
from ifcexport2.mesh import Mesh
import multiprocessing
import sys
import traceback
from dataclasses import asdict
import ifcopenshell
import ifcopenshell.geom
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Tuple, Union, Literal
from typing import Protocol
from ifcexport2.models import IRObject, ImportFailList, IfcFail

settings_dict = dict(USE_WORLD_COORDS=True, DISABLE_BOOLEAN_RESULT=False, WELD_VERTICES=True,
                     DISABLE_OPENING_SUBTRACTIONS=False,
                     NO_NORMALS=True, PRECISION=1e-7, VALIDATE=False, ELEMENT_HIERARCHY=True)


class Triangulation(Protocol):
    faces: list[int]
    verts: list[float]
    edges: list[int]


class TriangulationElement(Protocol):
    geometry: Triangulation
    type: str
    trx: list[float]
    product_id: int
    name: str
    parent_id: int
    context: str


import numpy as np
import ujson


def write_ir_to_file(objects: list[IRObject], fp, props=None, name="Group"):
    if props is None:
        props = {}
    root = create_three_js_root(name, props)





@dataclasses.dataclass(slots=True, frozen=True)
class ConvertArguments:
    ifc_doc: str
    backend: Literal['cgal','cgal-simple','opencascade'] | None = None
    scale: float = 1.0
    excluded_types: Tuple[str, ...] = ("IfcSpace","IfcOpeningElement")
    threads: int = 1
    settings: dict = dataclasses.field(default_factory=lambda: {**settings_dict})


@dataclasses.dataclass(slots=True, frozen=True)
class ConvertResult:
    success: bool
    objects: list[IRObject]
    meshes: list[Mesh]
    fails: ImportFailList


def convert(args: ConvertArguments) -> ConvertResult:
    ifc_file = ifc_loads(args.ifc_doc)
    settings = ifcopenshell.geom.settings()
    for k, v in args.settings.items():
        settings.set(getattr(settings, k), v)
    if args.backend is not None:
        iterator = ifcopenshell.geom.iterator(settings, ifc_file, num_threads=max(args.threads - 1, 1),
                                              geometry_library=args.backend)
    else:
        iterator = ifcopenshell.geom.iterator(settings, ifc_file, num_threads=max(args.threads - 1, 1))

    # Process geometry items
    success, objects, meshes, fails = process_ifc_geometry_items(
        geom_iterator=iterator,
        scale=args.scale,
        print_items=False,
        excluded_types=args.excluded_types
    )
    return ConvertResult(success, objects, meshes, fails)


def safe_call_fast_convert(ifc_string: str, scale: float = 1.0,
                           excluded_types: Tuple[str, ...] = ("IfcSpace",),
                           threads: int = 1,
                           settings: dict = None):
    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(convert, ConvertArguments(ifc_string, backend='cgal-simple', scale=scale,
                                                           excluded_types=excluded_types, threads=threads,
                                                           settings=settings))
        try:

            return future.result()
        except Exception as e:
            print(f"Fast method failed with exception: {e}")
            return convert(ConvertArguments(ifc_string, scale=scale, excluded_types=excluded_types, threads=threads,
                                            settings=settings))


def extract_color(itm):
    for mat in itm.geometry.materials:
        _color = mat.diffuse

        if hasattr(_color, 'a'):

            yield _color.r(), _color.g(), _color.b(), _color.a()
        else:
            yield _color.r(), _color.g(), _color.b()


def parse_geom_item(
        item: TriangulationElement, scale: float = 1.0
) -> Tuple[bool, IRObject, Union[Mesh, Tuple[str, str]]]:
    typ = item.type
    trx = item.transformation.matrix
    product_id = item.id
    name = item.name
    parent_id = item.parent_id
    context = item.context

    materials_colors = np.array(list(extract_color(item)), dtype=np.float32)
    try:
        geom = item.geometry
        faces = geom.faces
        verts = geom.verts
        #normals = geom.normals
        single_color = True

        verts = np.array(verts, dtype=np.float32).reshape((len(verts) // 3, 3))
        # normals = np.array(normals, dtype=np.float32).reshape((len(normals) // 3, 3))
        faces = np.array(faces, dtype=int).reshape((len(faces) // 3, 3))
        # if set(geom.material_ids).__len__()==1:
        #    single_color = True
        #    color=materials_colors[0]
        #    colors=np.zeros_like(verts)
        #    colors[...,:]=color
        #    #verts =  np.repeat(np.array(verts, dtype=np.float32).reshape((len(verts) // 3, 3)), 3, axis=0)
        #    #normals = np.array(normals, dtype=np.float32).reshape((len(normals) // 3, 3))
        #    #faces = np.array(faces, dtype=int).reshape((len(faces)//3,3))
        #

        single_color = False

        cols = materials_colors[np.array(geom.material_ids, dtype=int)]
        ccols = cols[np.arange(faces.shape[0]).repeat(3)]

        colors = np.zeros_like(verts)
        colors[faces] = ccols.reshape((*faces.shape, 3))

        msh = Mesh(
                verts * scale,
                faces=faces,
                # color=tuple(np.array(materials_colors[0]*255,dtype=int)),
                # normals=normals,
                colors=colors,
                uid=product_id,
            )


        ifc_object = IRObject(
            id=product_id,
            type=typ,
            name=name,
            context=context,
            parent_id=parent_id, mesh=msh,

            transform=trx,
        )
        return True, ifc_object, msh
    except RuntimeError as err:
        ifc_object = IRObject(
            id=product_id,
            type=typ,
            name=name,
            context=context,
            parent_id=parent_id,
            mesh=None,
            transform=trx,
        )
        tb = traceback.format_exc()
        return False, ifc_object, (str(err), tb)


def process_ifc_geometry_items(
        geom_iterator,
        scale: float,
        print_items: bool,
        excluded_types: Tuple[str, ...],
) -> Tuple[bool, List[IRObject], List[Mesh], ImportFailList]:
    objects: List[IRObject] = []
    meshes: List[Mesh] = []
    fails: List[IfcFail] = []

    if geom_iterator.initialize():
        i = 0
        j = 0
        while True:
            if print_items:
                print(f"Reading IFC: {i}", flush=True, end="\r")
            i += 1
            shape = geom_iterator.get()
            if shape.type not in excluded_types:
                success, attrs, mesh_or_tb = parse_geom_item(shape, scale=scale)
                if success:

                    objects.append(attrs)
                    meshes.append(mesh_or_tb)
                    j += 1
                else:
                    fails.append(IfcFail(item=attrs, tb=mesh_or_tb))

            if not geom_iterator.next():
                break
        if print_items:
            print()  # Move to the next line after progress
        if len(objects) == 0:
            return False, [], [], fails
        return True, objects, meshes, fails
    else:
        return False, [], [], []


def ifc_loads(txt: str):
    ifcfile = ifcopenshell.file.from_string(txt)
    return ifcfile


def ifc_load(f):
    if isinstance(f, str):
        with open(f, "r") as fl:
            txt = fl.read()
    else:
        txt = f.read()
    return ifc_loads(txt)


if __name__ == "__main__":

    def main():
        parser = argparse.ArgumentParser(
            description=(
                "Process an IFC file to extract geometric meshes and associated data.\n\n"
                "This script reads an IFC file, extracts geometry data, applies scaling, "
                "excludes specified types, and outputs mesh binaries, IFC databases, and failure logs."
            ),
            formatter_class=argparse.RawTextHelpFormatter,
        )

        # Required arguments
        parser.add_argument(
            "input_file",
            type=Path,
            help="Path to the input IFC file (e.g., 'model.ifc').",
        )

        # Optional arguments
        parser.add_argument(
            "-o",
            "--output-prefix",
            type=Path,
            default=None,
            help=(
                "Prefix for output files. If not specified, the input filename without extension "
                "is used."
            ),
        )
        parser.add_argument(
            "-s",
            "--scale",
            type=float,
            default=1.0,
            help="Scaling factor to apply to mesh vertices (default: 1.0).",
        )
        parser.add_argument(
            "-e",
            "--exclude",
            nargs="*",
            default=["IfcSpace", "IfcOpeningElement"],
            help=(
                "List of IFC types to exclude from processing. "
                "Default excludes 'IfcSpace'.\n"
                "Example: -e IfcSpace IfcSite IfcOpeningElement"
            ),
        )
        parser.add_argument(
            "-t",
            "--threads",
            type=int,
            default=multiprocessing.cpu_count(),
            help=(
                "Number of CPU threads to use for processing. "
                f"Default is the number of available CPUs: {multiprocessing.cpu_count()}."
            ),
        )
        parser.add_argument(
            "-p",
            "--print",
            action="store_true",
            help="Print progress information during processing.",
        )
        parser.add_argument(
            "--no-save-fails",
            action="store_true",
            help="Do not save failed items to the fails JSON file.",
        )
        parser.add_argument(
            "--json-output",
            action="store_true",
            help="Outputs the result in a single json string. Suitable for scripts.",
        )
        args = parser.parse_args()

        input_file: Path = args.input_file
        if not input_file.is_file():
            print(f"Error: Input file '{input_file}' does not exist.", file=sys.stderr)
            sys.exit(1)

        output_prefix: Path = (
            args.output_prefix
            if args.output_prefix is not None
            else input_file.with_suffix("")
        )

        print_items: bool = args.print
        save_fails: bool = not args.no_save_fails

        import ifcopenshell
        import ifcopenshell.geom
        # Open the IFC file
        try:
            with open(input_file, 'r') as f:
                ifc_string = f.read()

            # ifc_file = ifcopenshell.open(str(input_file))
        except Exception as e:
            print(f"Error opening IFC file: {e}", file=sys.stderr)
            sys.exit(1)

        # Create geometry iterator

        # Process geometry items
        result = safe_call_fast_convert(ifc_string, scale=args.scale, excluded_types=args.exclude, threads=args.threads,
                                        settings=settings_dict)
        success, objects, meshes, fails = result.success, result.objects, result.meshes, result.fails
        output_files = []
        if not success:
            if print_items:
                print("Failure: No objects were extracted.", file=sys.stderr)
                sys.exit(1)
        else:
            if print_items:
                print("Success: Objects extracted.")

        # Write meshes to file
        # mesh_output_file = output_prefix.with_suffix(".mesh.bin")

        try:
            root = create_three_js_root(Path(args.input_file).stem)
            for o in objects:
                msh = mesh_to_three(o.mesh,
                                    {"name": o.name, "type": o.type, "parent_id": o.parent_id, "context": o.context,
                                     "id": o.id}, name=o.name, matrix=o.transform, color=o.mesh.color)
                add_mesh(root, *msh)
            mesh_output_file = output_prefix.with_suffix(".viewer.json")
            with open(mesh_output_file, 'w') as f:
                import json
                json.dump(root, f)

            if print_items:
                print(f"{mesh_output_file} saved.")
            # output_files.append(mesh_output_file)

        except Exception as e:
            print(f"Error writing mesh file: {e}", file=sys.stderr)
            raise e
        # Write IFC database to JSON
        ifcdb_output_file = output_prefix.with_suffix(".ifcdb.pkl")
        try:
            with ifcdb_output_file.open("wb") as f:
                import pickle
                pickle.dump(objects, f, protocol=pickle.HIGHEST_PROTOCOL)
                # ujson.dump([asdict(o) for o in objects], f,ensure_ascii=False)
            if print_items:
                print(f"{ifcdb_output_file} saved.")
            output_files.append(ifcdb_output_file)
        except Exception as e:
            print(f"Error writing IFC DB file: {e}", file=sys.stderr)

        # Write fails to JSON if requested
        if save_fails:
            fails_output_file = output_prefix.with_suffix(".fails.json")
            try:
                with fails_output_file.open("w") as f:
                    fails_serializable = [
                        {"item": asdict(fail.item), "traceback": fail.tb}
                        for fail in fails
                    ]
                    ujson.dump(fails_serializable, f, ensure_ascii=False)
                output_files.append(fails_output_file)
                if print_items:
                    print(f"{fails_output_file} saved.")

            except Exception as e:

                print(f"Error writing fails file: {e}", file=sys.stderr)

        if print_items:
            print("Processing completed successfully.")

        if args.json_output:
            import json
            print(json.dumps([fl.__str__() for fl in output_files], ensure_ascii=False))


    main()

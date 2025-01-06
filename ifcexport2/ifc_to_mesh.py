from __future__ import annotations

import argparse
import dataclasses
import json

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
    name: str = "Model"


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
                           settings: dict = None,name="Model"):

    return convert(ConvertArguments(ifc_string, scale=scale, excluded_types=excluded_types, threads=threads,
                                            settings=settings,name=name))


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

def create_viewer_object(name, objects):
    root = create_three_js_root(name)
    for o in objects:
                msh = mesh_to_three(
                    o.mesh,
                    {
                        "name": o.name,
                        "type": o.type,
                        "parent_id": o.parent_id,
                        "context": o.context,
                        "id": o.id
                    },
                    name=o.name,
                    matrix=o.transform,
                    color=o.mesh.color
                )
                add_mesh(root, *msh)
    return root

def ifc_load(f):
    if isinstance(f, str):
        with open(f, "r") as fl:
            txt = fl.read()
    else:
        txt = f.read()
    return ifc_loads(txt)


from pathlib import Path
import click
from ifcexport2.compat import IfcExportCompat
def cli_export(
    input_file: Path,
    output_prefix: Path,
    output_format:IfcExportCompat,
    scale: float,
    exclude: tuple,
    threads: int,
    print_items: bool,
    no_save_fails: bool,
    json_output: bool,
):
    """
    Process an IFC file to extract geometric meshes and associated data.
    """
    if not input_file.is_file():
        print(f"Error: Input file '{input_file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        import ifcopenshell
        import ifcopenshell.geom
    except ImportError as e:
        print(f"Error importing required modules: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output prefix
    output_prefix = output_prefix if output_prefix is not None else input_file.with_suffix("")

    save_fails = not no_save_fails

    # Open the IFC file
    try:
        with open(input_file, 'r') as f:
            ifc_string = f.read()

        # ifc_file = ifcopenshell.open(str(input_file))
    except Exception as e:
        print(f"Error opening IFC file: {e}", file=sys.stderr)
        sys.exit(1)

    # Create geometry iterator
    # (Assuming `safe_call_fast_convert` and `settings_dict` are defined elsewhere)

    result = safe_call_fast_convert(
            ifc_string,
            scale=scale,
            excluded_types=tuple(exclude),
            threads=threads,
            settings=settings_dict,name=input_file.stem
        )


    success, objects, meshes, fails = result.success, result.objects, result.meshes, result.fails
    output_files = []

    if not success:
        if print_items:
            if len(fails) > 0:

                    print(f"Failure: Error during geometry conversion: {result.fails}", file=sys.stderr)
            else:
                    print(f"Failure: IfcOpenShell crashed on all attempts. No objects were extracted.", file=sys.stderr)


        sys.exit(1)
    else:
        if print_items:
            print(f"Success: {len(result.objects)} objects extracted. {len(result.fails)} fails")

    # Write meshes to file
    if output_format.viewer:
        try:

            root=create_viewer_object(input_file.stem,objects)
            mesh_output_file = output_prefix.with_suffix(".viewer.json")
            with open(mesh_output_file, 'w') as f:
                json.dump(root, f)
        except Exception as e:
                print(f"Error writing mesh file: {e}", file=sys.stderr)
                raise e

    else:
            raise NotImplementedError(f"{str(output_format)} method of export is not supported at the moment")
    if print_items:
            print(f"{mesh_output_file} saved.")
        # output_files.append(mesh_output_file)


    # Write IFC database to JSON
    # Uncomment and modify if needed
    # ifcdb_output_file = output_prefix.with_suffix(".objects")
    # try:
    #     with ifcdb_output_file.open("wb") as f:
    #         import pickle
    #         pickle.dump([asdict(o) for o in objects], f, protocol=pickle.HIGHEST_PROTOCOL)
    #
    #     if print_items:
    #         print(f"{ifcdb_output_file} saved.")
    #     output_files.append(ifcdb_output_file)
    # except Exception as e:
    #     print(f"Error writing IFC DB file: {e}", file=sys.stderr)

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

    if json_output:
        print(json.dumps([str(fl) for fl in output_files], ensure_ascii=False))




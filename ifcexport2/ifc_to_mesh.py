from __future__ import annotations

import argparse
import dataclasses
import gc
import json
import os

import rich

from ifcexport2.ifc_styles import build_surf_style_data
from ifcexport2.mesh_to_three import create_three_js_root, mesh_to_three, add_mesh, create_group, get_property, \
    add_material, material, default_material, add_geometry, color_attr_material
from ifcexport2.mesh import Mesh
import multiprocessing
import sys
import traceback
from dataclasses import asdict
import ifcopenshell
import ifcopenshell.geom

import ifcopenshell.util.element
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Tuple, Union, Literal, NamedTuple,Any
from typing import Protocol
from ifcexport2.models import IRGeometryObject, ImportFailList, IfcFail
NO_OCC=bool(os.getenv("NO_OCC",0))
from ifcexport2.settings import ifcopenshell_default_settings_dict  as settings_dict

import gc
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


def write_ir_to_file(objects: list[IRGeometryObject], fp, props=None, name="Group"):
    if props is None:
        props = {}
    root = create_three_js_root(name, props)





@dataclasses.dataclass(slots=True, frozen=True)
class ConvertArguments:
    ifc_doc: str|Any
    backend: Literal['cgal','cgal-simple','opencascade'] | None = None if NO_OCC else "opencascade"
    scale: float = 1.0
    excluded_types: list[str] = dataclasses.field(default_factory=lambda :["IfcSpace","IfcOpeningElement"])
    threads: int = min(os.cpu_count(), 4)
    settings: dict = dataclasses.field(default_factory=lambda: {**settings_dict})
    name: str = "Model",
    is_file_path:bool=False


@dataclasses.dataclass(slots=True, frozen=True)
class ConvertResult:
    success: bool
    objects: list[IRGeometryObject]
    meshes: list[Mesh]
    materials:dict[str,dict]
    fails: ImportFailList




def convert(args: ConvertArguments) -> ConvertResult:
    if isinstance(args.ifc_doc,str):

        ifc_file = ifc_loads(args.ifc_doc, is_path=False)
    else:

        ifc_file=args.ifc_doc

    surfs_styles,styled_items,elems_styles=build_surf_style_data(ifc_file)
    print(surfs_styles)
    print(elems_styles)
    settings = ifcopenshell.geom.settings()
    #settings.set("use-python-opencascade", not NO_OCC)

    for k, v in args.settings.items():

        settings.set(getattr(settings, k, k), v)

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
        excluded_types=tuple(args.excluded_types),styled_items=elems_styles,surfs_styles=surfs_styles
    )
    del iterator
    del ifc_file
    del args
    gc.collect(

    )

    return ConvertResult(success, objects, meshes, materials={mat['uuid']:mat for (cols,mat) in surfs_styles.values()}, fails=fails)


def safe_call_fast_convert(ifc_string: str, scale: float = 1.0,
                           excluded_types: Tuple[str, ...] = ("IfcSpace",),
                           threads: int = min(6,os.cpu_count()-2),
                           settings: dict = None,name="Model", is_file_path:bool=False):

    return convert(ConvertArguments(ifc_string, scale=scale, excluded_types=excluded_types, threads=threads,
                                            settings=settings,name=name,is_file_path=is_file_path))


def convert_from_file_path(ifc_fp: str, scale: float = 1.0,
                           excluded_types: Tuple[str, ...] = ("IfcSpace",),
                           threads: int = min(6, os.cpu_count() - 2),
                           settings: dict = None, name="Model", is_file_path: bool = False):
    print(f'from fp: {ifc_fp}')
    return convert(ConvertArguments(ifcopenshell.open(ifc_fp), scale=scale, excluded_types=excluded_types, threads=threads,
                                    settings=settings, name=name, is_file_path=is_file_path))


def extract_color(itm):

    for mat in itm.geometry.materials:

        _color = mat.diffuse
        #print(_color,mat)

        if hasattr(_color, 'a'):

            yield _color.r(), _color.g(), _color.b(), _color.a()
        else:
            yield _color.r(), _color.g(), _color.b()

def flat_verts_faces_cols(vertices,faces,fcol):
    #print(vertices.shape,faces.shape,fcol.shape)
    flat_indices = faces.reshape(-1)  # length 3 M
    flat_positions = vertices[flat_indices]  # (3 M, 3)

    flat_colours = np.repeat(fcol, 3, axis=0)
    new_faces = np.arange(flat_indices.shape[0],dtype=int)
    return flat_positions,new_faces,np.array(flat_colours,dtype=float)



def parse_geom_item(
        item: TriangulationElement, scale: float = 1.0,       styled_items:dict[int,int]=None,surfs_styles=None,
) -> Tuple[bool, IRGeometryObject, Union[Mesh, Tuple[str, str]]]:
    typ = item.type
    trx = item.transformation.matrix
    product_id = item.id
    name = item.name
    parent_id = item.parent_id
    context = item.context

    if trx!=(1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0):
        ...
    mat=None
    single_material=False
    materials_colors=None

    if styled_items.get(item.id) is not None :

        if len(styled_items[item.id])>1:
            print("style",styled_items[item.id])
            materials_colors = np.array(list(extract_color(item)), dtype=float)
            mat=color_attr_material
            print(len(styled_items[item.id]),styled_items[item.id])
            single_material = False

        else:
            materials_colors,mat=surfs_styles[styled_items[item.id][0]]
            single_material=True

    else:
        
        materials_colors = np.array(list(extract_color(item)), dtype=float)
        if len(materials_colors)==0:
            mat = default_material
        elif len(materials_colors)>1:
            mat = color_attr_material
        else:
            mat=default_material
        #materials_colors = np.array([[200/255,200/255,200/255]], dtype=float)



    try:
        geom = item.geometry
        faces = geom.faces
        verts = geom.verts
        if len(faces )==0 or len(verts) ==0:
            ifc_object = IRGeometryObject(
                id=product_id,
                type=typ,
                name=name,
                context=context,
                parent_id=parent_id,
                mesh=None,
                transform=trx,
            )
            return False, ifc_object, ("empty mesh","")
        #normals = geom.normals


        verts = np.array(verts, dtype=float).flatten().reshape((len(verts) // 3, 3))
        # normals = np.array(normals, dtype=np.float32).reshape((len(normals) // 3, 3))
        faces = np.array(faces, dtype=int).flatten().reshape((len(faces) // 3, 3))

        if materials_colors is None or len(materials_colors)==0:
            msh = Mesh(
                verts * scale,
                faces=faces,
                # normals=normals,
                #colors=c,
                uid=product_id,
                transform=trx,
                material=default_material
            )
        elif len(materials_colors)==1:

             #color=tuple(materials_colors[0].tolist())

             #colors = np.zeros_like(verts)
             #colors[..., :] = materials_colors[0]



             msh = Mesh(
                 verts * scale,
                 faces=faces,
                 #color=(int(color[0]*255),int(color[1]*255),int(color[2]*255)),
                 # normals=normals,
                 colors=None,
                 uid=product_id,
                 transform=trx,
                 material=material(tuple(np.array(materials_colors[0]*255,dtype=int).tolist()))


             )

        #
        #    #verts =  np.repeat(np.array(verts, dtype=np.float32).reshape((len(verts) // 3, 3)), 3, axis=0)
        #    #normals = np.array(normals, dtype=np.float32).reshape((len(normals) // 3, 3))
        #    #faces = np.array(faces, dtype=int).reshape((len(faces)//3,3))
        #
        else:
            #print('ccccc')

            #cols = (materials_colors[np.array(geom.material_ids, dtype=int)]*255).astype(int)

            ccols = materials_colors[np.array(geom.material_ids,dtype=int)]
            #print(  max(geom.material_ids),materials_colors.shape)
            #print(ccols)
            v,f,c=flat_verts_faces_cols(verts,faces,ccols)
            v, f, c=v.reshape((-1,3)),f.reshape((-1,3)),c.reshape((-1,3))

            #print(c)

            msh = Mesh(
                v* scale,
                faces=f,
                # color=tuple(np.array(materials_colors[0]*255,dtype=int)),
                # normals=normals,
                colors=c,
                uid=product_id,
                transform=trx ,
                material=mat
            )


        ifc_object = IRGeometryObject(
            id=product_id,
            type=typ,
            name=name,
            context=context,
            parent_id=parent_id, mesh=msh,

            transform=trx,
        )
        return True, ifc_object, msh
    except RuntimeError as err:
        ifc_object = IRGeometryObject(
            id=product_id,
            type=typ,
            name=name,
            context=context,
            parent_id=parent_id,
            mesh=None,
            transform=trx,
        )
        tb = traceback.format_exc()
        print(err)
        print(tb)
        return False, ifc_object, (str(err), tb)


def process_ifc_geometry_items(
        geom_iterator,
        scale: float,
        print_items: bool,
        excluded_types: Tuple[str, ...],
        styled_items:dict[int,int],surfs_styles:dict
) -> Tuple[bool, List[IRGeometryObject], List[Mesh], ImportFailList]:
    objects: List[IRGeometryObject] = []
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
                success, attrs, mesh_or_tb = parse_geom_item(shape, scale=scale,styled_items=styled_items,surfs_styles=surfs_styles)
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


def ifc_loads(txt: str, is_path:bool=False):
    if is_path:
        return ifcopenshell.open(txt)
    ifcfile = ifcopenshell.file.from_string(txt)
    return ifcfile

import     ifcexport2.ifc_psets
import re

def _build(three_js_root:dict, h: ifcexport2.ifc_hierarchy.Hierarchy, geoms:dict[int,IRGeometryObject], materials:dict[str,dict],ifc_file:ifcopenshell.file):

    add_material(three_js_root, default_material)
    add_material(three_js_root,color_attr_material)
    for i in materials.values():
        add_material(three_js_root,i)
    root = three_js_root['object']
    roots_stack = [(root, list(h.root_elements))]
    while roots_stack:
        current_root, next_roots = roots_stack.pop()
        next_roots.reverse()
        current_root_id=get_property(current_root, 'id')

        for obj_id in next_roots:

            obj_childs = h.hierarchy.get(obj_id, [])
            additional_props = {}
            if current_root_id is not None:
                additional_props={"parent_id":current_root_id}


            props=ifcexport2.ifc_psets.extract_props(obj_id,ifc_file,additional_props)

            if len(obj_childs) > 0:

                obj_o = create_group(props['name'], props)



                roots_stack.append((obj_o, obj_childs))

            else:

                o = geoms[obj_id]

                obj_o ,obj_geom,obj_mat= mesh_to_three(
                    o.mesh,
                    name=props['name'],

                    props=props)

                #obj_o['material']=mat['uuid']


                add_geometry(three_js_root, obj_geom)

            current_root['children'].append(obj_o)




import ifcexport2.ifc_hierarchy

def create_viewer_object(name, objects:list[IRGeometryObject],materials,ifc_file:ifcopenshell.file,include_spatial_hierarchy:bool=True):
    geoms={o.id :o for o in objects}

    ifc_hierarchy=ifcexport2.ifc_hierarchy.clean_hierarchy(
        ifcexport2.ifc_hierarchy.build_hierarchy(ifc_file,
                                                 include_spatial_hierarchy=include_spatial_hierarchy
                                                 ),
        list(geoms.keys())
    )

    root = create_three_js_root(name,{'name':name})
    _build(root,ifc_hierarchy,geoms=geoms,materials=materials,ifc_file=ifc_file)

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
        rich.print(f"[red]Error: Input file '{input_file}' does not exist.[/red]", file=sys.stderr)
        sys.exit(1)

    try:
        import ifcopenshell
        import ifcopenshell.geom
    except ImportError as e:
        rich.print(f"[red]Error importing required modules: {e}[/red]", file=sys.stderr)
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
        rich.print(f"[red]Error opening IFC file: {e}[/red]", file=sys.stderr)
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

                    rich.print(f"[red]Failure: Error during geometry conversion: {result.fails}[/red]", file=sys.stderr)
            else:
                    rich.print(f"[red]Failure: IfcOpenShell crashed on all attempts. No objects were extracted.[/red]", file=sys.stderr)


        sys.exit(1)
    else:
        if print_items:
            print(f"Success: {len(result.objects)} objects extracted. {len(result.fails)} fails")

    # Write meshes to file
    if output_format.viewer:
        try:
            ifc_file = ifcopenshell.file.from_string(ifc_string)

            root=create_viewer_object(input_file.stem,
                                      objects,
                                      ifc_file
                                      )
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




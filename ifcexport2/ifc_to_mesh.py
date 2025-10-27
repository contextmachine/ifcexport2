from __future__ import annotations

import argparse
import dataclasses
import gc
import json
import os

import rich

from ifcexport2.ifc_preprocess import preprocess_ifc, IfcInfo
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
from typing import List, Tuple, Union, Literal, NamedTuple, Any, Optional, Iterator
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
class ConvertResult:
    success: bool
    objects: list[IRGeometryObject]
    info: IfcInfo
    
    # fails:ImportFailList


@dataclasses.dataclass(slots=True, frozen=True)
class ConvertArguments:
    excluded_types: list[str] = dataclasses.field(default_factory=lambda :["IfcSpace","IfcOpeningElement"])
    name: str = "Model",
    target_units:Optional[str]=None
    
    





from tqdm import tqdm
from ifcopenshell.util.unit import convert_file_length_units, convert_unit
from ifcopenshell.util.unit import convert as ifcopsh_convert
OUTPUT_UNITS = "MILLIMETER"
def convert(
        ifc_file:ifcopenshell.file,
    args: ConvertArguments,
        settings: dict = None,
    threads=None,
    verbose=False,
backend=None,
    
) -> ConvertResult:
    
    if settings is None:
        if verbose:
            rich.print(f"Using default settings.")
        settings={**settings_dict}
        if verbose:
            rich.print(settings)
    info = preprocess_ifc(ifc_file, args.excluded_types)
    print(info)
    if args.target_units is not None:
        ifc_file = convert_file_length_units(ifc_file, args.target_units)
        info = preprocess_ifc(ifc_file, args.excluded_types)
        print('info new',info)
    used_settings = ifcopenshell.geom.settings()
    if threads is None:
        threads = multiprocessing.cpu_count() - 1
    threads = max(threads, 1)
    for k, v in settings.items():
        used_settings.set(getattr(used_settings, k), v)
    #used_settings.set("convert-back-units", True)
    if verbose:
        rich.print(f"Using {threads} threads for processing.")
        rich.print(f"settings:\n{used_settings}")
    if backend is not None:
        iterator = ifcopenshell.geom.iterator(
            used_settings,
            ifc_file,
            num_threads=threads,
            geometry_library=backend,
        )
    else:
        iterator = ifcopenshell.geom.iterator(used_settings, ifc_file, num_threads=threads)
    itr = process_ifc_geometry_items(
        geom_iterator=iterator,
        excluded_types=args.excluded_types,
    
    )
    if verbose:
        total = info.product_count
        # --- pre-count only metadata (very fast, no geometry)

        itr = tqdm(
            itr,
            desc="ifc processing",
            dynamic_ncols=True,
            colour="#1d6acf",
            total=total,
        )
    items=list(itr)
    
  
        
    return ConvertResult(len(items)>0,items,info)


def safe_call_fast_convert(
    ifc_string: str,
    mesh_file_path: str,
    excluded_types: list[str] = None,
    threads=None,
    settings: dict = None,
    verbose: bool = False,
):
    if excluded_types is None:
        excluded_types = ["IfcSpace", "IfcOpeningElement"]

    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            convert,
            ConvertArguments(
                ifc_string,
                backend=None,
                excluded_types=excluded_types,
                settings=settings,
                mesh_file_path=mesh_file_path,
            ),
            verbose=verbose,
            threads=threads,
        )
        try:

            return future.result()
        except Exception as e:
            print(f"Fast method failed with exception: {e}")
            return convert(
                ConvertArguments(
                    ifc_string,
                    excluded_types=excluded_types,
                    settings=settings,
                    mesh_file_path=mesh_file_path,
                ),
                threads=1,
                verbose=verbose,
            )


import ifcopenshell.util
import ifcopenshell.util.element


def extract_psets(ifc_element) -> dict[str]:

    psets = ifcopenshell.util.element.get_psets(ifc_element)
    return psets


def combine_transform(t1: np.ndarray, t2: np.ndarray) -> np.ndarray:
    """
    Combine two 4x4 transforms into one.
    Semantics (row-vector pipeline as used in transform_nurbs):
      result = t2 @ t1    # applying t1, then t2.
    """
    T1 = np.asarray(t1, dtype=float)
    T2 = np.asarray(t2, dtype=float)
    if T1.shape != (4, 4) or T2.shape != (4, 4):
        raise ValueError("Both t1 and t2 must have shape (4,4).")
    return T2 @ T1


def scale_matrix(factor):
    S = np.eye(4)
    S[:3, :3] *= factor
    return S


from ifcopenshell.entity_instance import entity_instance






def extract_color(itm):
    for mat in itm.geometry.materials:
        _color = mat.diffuse

        if hasattr(_color, 'a'):

            yield _color.r(), _color.g(), _color.b(), _color.a()
        else:
            yield _color.r(), _color.g(), _color.b()


def parse_geom_item(
        item: TriangulationElement, scale: float = 1.0
) -> Tuple[bool, IRGeometryObject, Union[Mesh, Tuple[str, str]]]:
    typ = item.type
    trx =  (np.reshape(item.transformation.matrix, (4, 4), order="F"),)
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
        print(err)
        tb = traceback.format_exc()
        return False, ifc_object, (str(err), tb)


def process_ifc_geometry_items(
    geom_iterator,
    excluded_types: list[str],

    **kwargs,
):

    if geom_iterator.initialize():
        i = 0
        j = 0
        while geom_iterator.next():
            # if print_items:
            # print(f"Reading IFC: {i}", flush=True, end="\r")
            i += 1
            shape = geom_iterator.get()
            if shape.type not in excluded_types:
                success, obj, mesh_or_tb = parse_geom_item(
                    shape
                )
              
                if success:
                    yield obj
                else:
                    rich.print(f'[red][bold]import fail: {obj}[/bold][/red]')
                
        return None
    else:
        rich.print('[red][bold]geometry iterator are not initialized![/bold][/red]')
        return None


def ifc_loads(txt: str, is_path:bool=False):
    if is_path:
        return ifcopenshell.open(txt)
    ifcfile = ifcopenshell.file.from_string(txt)
    return ifcfile

import     ifcexport2.ifc_psets
import re

def _build(three_js_root:dict, h: ifcexport2.ifc_hierarchy.Hierarchy, geoms:dict[int,IRGeometryObject],ifc_file:ifcopenshell.file):

    add_material(three_js_root, default_material)
    add_material(three_js_root,color_attr_material)
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
                if o.mesh.colors is None:
                   mat =default_material
                else :
                    mat = color_attr_material

                obj_o ,obj_geom,obj_mat= mesh_to_three(
                    o.mesh,
                    name=props['name'],
                    matrix=o.transform,
                    props=props)

                obj_o['material']=mat['uuid']
                add_geometry(three_js_root, obj_geom)
            current_root['children'].append(obj_o)




import ifcexport2.ifc_hierarchy

def create_viewer_object(name, objects:list[IRGeometryObject],ifc_file:ifcopenshell.file,include_spatial_hierarchy:bool=True):
    geoms={o.id :o for o in objects}

    ifc_hierarchy=ifcexport2.ifc_hierarchy.clean_hierarchy(
        ifcexport2.ifc_hierarchy.build_hierarchy(ifc_file,
                                                 include_spatial_hierarchy=include_spatial_hierarchy
                                                 ),
        list(geoms.keys())
    )
    root = create_three_js_root(name,{'name':name})
    _build(root,ifc_hierarchy,geoms,ifc_file)
    
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
    exclude: tuple,
    threads: int,
    print_items: bool,
    json_output: bool,
        target_units:str=None,
        
        **kwargs
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

   

    # Open the IFC file
   
    ifc_file = ifcopenshell.open(str(input_file))
  

    # Create geometry iterator
    # (Assuming `safe_call_fast_convert` and `settings_dict` are defined elsewhere)

    result = convert(ifc_file,ConvertArguments(
      
         
            excluded_types=list(exclude),
           
           name=input_file.stem,target_units=target_units), settings=settings_dict,
                     threads=threads,verbose=True
                     
        )
    
    
    success, objects = result.success, result.objects
    output_files = []
   
    if not success:
        if print_items:
            rich.print(f"[red]Failure: IfcOpenShell crashed on all attempts. No objects were extracted.[/red]", file=sys.stderr)


        sys.exit(1)
        
    else:
        if print_items:
            print(f"Success: {len(result.objects)} objects extracted. {len(result.fails)} fails")

    # Write meshes to file
    if output_format.viewer:
        try:
            

            root=create_viewer_object(input_file.stem,
                                      objects,
                                      ifcopenshell.open(str(input_file))
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
  

    if print_items:
        print("Processing completed successfully.")

    if json_output:
        print(json.dumps([str(fl) for fl in output_files], ensure_ascii=False))




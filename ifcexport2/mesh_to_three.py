import uuid
from datetime import datetime

import numpy as np
from .mesh import Mesh

def material(color_rgb, flat=True):
    return {
        "uuid": uuid.uuid4().__str__(),
        "type": "MeshStandardMaterial",
        "color": int(rgb_to_dec(*color_rgb)),
        "roughness": 0.8,
        "metalness": 0.88,
        "emissive": 0,
        "envMapRotation": [0, 0, 0,
                           "XYZ"],
        "envMapIntensity": 1,
        "side": 2,
        "blendColor": 0,
        "flatShading": flat
    }
def rgb_to_dec(r, g, b):
    return (r << 16) + (g << 8) + b
color_attr_material={
        "uuid": uuid.uuid4().__str__(),
        "type": "MeshStandardMaterial",
        "color": int(rgb_to_dec(225,225,225)),
        "roughness": 0.2,
        "metalness": 0.5,
        "emissive": 0,
        "envMapRotation": [0, 0, 0,
                           "XYZ"],
        "envMapIntensity": 1,
        "side": 2,
         "vertexColors": True,
    "blendColor": 0,
    "flatShading": True

    }
default_material=material((150,150,150))
_material_table={(150,150,150):default_material}

def mesh_to_three(mesh:Mesh,  props:dict=None,name="MeshObject",color=None, mat=None,matrix=None):
    mesh_geometry_uid=uuid.uuid4().__str__()

    geom={
        "uuid":  mesh_geometry_uid,
        "type": "BufferGeometry",
        "data": {
            "attributes": {
                "position": {
                    "itemSize": 3,
                    "type": "Float32Array",
                    "array": np.array(mesh.position,dtype=float).flatten().tolist()
                           }
            },
                "index": {"itemSize": 1,
                           "type": "Uint32Array",
                           "array": [int(i) for i in np.array(mesh.faces.flatten(),dtype=np.uint32)]
                           }

            }



    }
    if mesh.colors is not None:
        colors={
            "itemSize":int( mesh.colors.shape[-1]),
            "type": "Float32Array",
            "array": np.array(mesh.colors, dtype=float).flatten().tolist()
        }
        geom['data']['attributes']['color']=colors
    if color is not None:
        if color not in _material_table:

            _material_table[color]=material(color)

        mat=_material_table[color]
    elif mat is not None :
        mat=mat
    elif mesh.colors is not None:
        mat=color_attr_material
    else:
        mat=default_material

    mesh_object={
            "uuid": uuid.uuid4().__str__(),
            "type": "Mesh",
            "name": name,
            "layers": 1,
            "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1] if matrix is None else list(matrix),
            "up": [0, 1, 0],
            "userData":{"properties":props if props is not None else {}},
            "geometry": mesh_geometry_uid,
            "material": mat["uuid"],
        }

    return mesh_object,geom,mat



def create_three_js_root(name:str= "Object", props=None):
    return {
    "metadata": {
        "version": 4.6,
        "type": "Object",
        "generator": "Object3D.toJSON"
    },
        'geometries':[],
        'materials': [],
        "object":{"type":"Group", "uuid":uuid.uuid4().__str__(),"children":[], "layers": 1,
        "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "up": [0, 1, 0],   "name": name, "userData": {"properties": props if props is not None else {}},}
    }
def add_material(root:dict, mat:dict):
    if mat['uuid']in [m['uuid'] for m in root['materials']]:
        return
    root['materials'].append(mat)


def add_geometry(root: dict, geom: dict):
    if geom['uuid'] in [g['uuid'] for g in root['geometries']]:
        return
    root['geometries'].append(geom)

def add_mesh(root:dict, obj:dict, geom:dict, mat:dict):
    root['object']['children'].append(obj)
    add_geometry(root, geom)
    add_material(root, mat)


def add_group(root:dict, obj:dict):
    root['object']['children'].append(obj)



def generate_update_queries(current_objects, object_uuids,key='collision'):
    updated_props={}
    deleted_props =[]
    current_time = datetime.now().isoformat()
    # Identify objects to activate/update and deactivate
    to_activate = set(object_uuids)
    to_deactivate = set(current_objects.keys()) - to_activate
    # Query 1: Activate and update objects
    query_activate = {
        "object_uuids": list(to_activate),
        "updated_props": {**updated_props, key: True},
        "deleted_props": deleted_props
    }
    # Query 2: Deactivate objects
    query_deactivate = {
        "object_uuids": list(to_deactivate),
        "updated_props": {key: current_time},
        "deleted_props": list(updated_props.keys())  # Remove updated properties
    }
    return query_activate, query_deactivate

'''
# Example usage
current_objects = {
    "853cdc79-bb52-489b-a576-352dc6899bc3": {
        "prop1": "old-value",
        "collision": False,
"prop3":3,
    },
    "another-uuid": {
        "prop2": "old-value2",
        "collision":  "2024-11-01T13:00:00",
    },
}
object_uuids = ["853cdc79-bb52-489b-a576-352dc6899bc3"]

'''


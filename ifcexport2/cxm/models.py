from __future__ import annotations
from __future__ import unicode_literals
import sys
import uuid
from uuid import uuid4

sys.setrecursionlimit(10000)

from typing import List, Dict, Optional, Union, Tuple, Any
from dataclasses import dataclass, field, is_dataclass
from typing import List, Dict
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class PropsData:
    object_uuids: List[str]|List[int]=field(default_factory=list)
    updated_props: Dict[str, str]=field(default_factory=dict)
    deleted_props: List[str]=field(default_factory=list)
@dataclass_json
@dataclass
class Endpoint:
    type: str
    entry: str
    query: str = ""

@dataclass_json
@dataclass
class UpdatePropsBody:
    scene_id: int
    user_id: int
    model_id: int
    endpoint: Endpoint
    props_data: PropsData



@dataclass_json
@dataclass
class UserData:
    properties: Dict[str, str]=field(default_factory=dict)
    endpoints: Dict[str, Endpoint]=field(default_factory=dict)



@dataclass_json
@dataclass
class Metadata:
    version: float = 4.5
    type: str="Object"
    generator: str="Object3D.toJSON"


@dataclass_json
@dataclass
class AttributeData:
    itemSize: int
    type: str
    array: List[float]
    normalized: bool

@dataclass_json
@dataclass
class IndexData:
    #itemSize: int
    type: str
    array: List[float]



@dataclass_json
@dataclass
class BoundingSphere:
    center: List[float]
    radius: float


@dataclass_json
@dataclass
class GeometryData:
    attributes: Dict[str, AttributeData]
    boundingSphere: Optional[BoundingSphere] = None
    index: Optional[IndexData] = None

@dataclass_json
@dataclass
class Geometry:
    uuid: str
    type: str
    data: GeometryData


@dataclass_json
@dataclass
class Material:
    uuid: str
    type: str


    color: int = 8553090
    side:int=2
    flatShading:bool= True
    emissive: Optional[int] = None
    specular: Optional[int] = None
    shininess: Optional[float] = None
    envMapRotation: Optional[List[Union[float, str]]] = None
    reflectivity: Optional[float] = None
    refractionRatio: Optional[float] = None
    vertexColors: Optional[bool] = None
    blendColor: Optional[int] = None
    roughness: Optional[float] = None
    metalness: Optional[float] = None
    sheen: Optional[float] = None
    sheenColor: Optional[int] = None
    sheenRoughness: Optional[float] = None
    specularIntensity: Optional[float] = None
    specularColor: Optional[int] = None
    clearcoat: Optional[float] = None
    clearcoatRoughness: Optional[float] = None
    dispersion: Optional[float] = None
    iridescence: Optional[float] = None
    iridescenceIOR: Optional[float] = None
    iridescenceThicknessRange: Optional[List[float]] = None
    anisotropy: Optional[float] = None
    anisotropyRotation: Optional[float] = None
    envMapIntensity: Optional[float] = None
    transmission: Optional[float] = None
    thickness: Optional[float] = None
    attenuationColor: Optional[int] = None




@dataclass_json
@dataclass
class GeometryObject:
    uuid: str
    type: str
    name: str
    geometry: str
    material: str
    layers: int =0
    matrix: List[float]=field(default_factory = lambda :[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.])
    up: List[float] = field(default_factory=lambda :[0, 1, 0])
    children: Optional[List[GeometryObject]]=None

    def get_geometry(self, root:Object3DJSON)->Geometry|None:
        for r in root.geometries:
            if r.uuid==self.geometry:
                return r

    def get_material(self, root: Object3DJSON) -> Material|None:
        for r in root.materials:
            if r.uuid == self.material:
                return r



@dataclass_json
@dataclass
class ObjectData:
    uuid: str =field(default_factory=lambda :uuid4().hex)
    type: str = "Object3D"
    name: str = "Object"

    layers: int=1
    userData: UserData = field(default_factory=UserData)
    matrix: List[float]=field(default_factory = lambda :[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.])
    up: List[float] = field(default_factory=lambda :[0, 1, 0])
    children: Optional[List[Union[ObjectData,GeometryObject]] ]= None
    geometry: Optional[str] = None
    material: Optional[str] = None

    def get_geometry(self, root:Object3DJSON)->Geometry|None:
        for r in root.geometries:
            if r.uuid==self.geometry:
                return r

    def get_material(self, root: Object3DJSON) -> Material|None:
        for r in root.materials:
            if r.uuid == self.material:
                return r

    def add_update_props_handle(self,url):
        self.userData.endpoints['']

@dataclass_json
@dataclass
class Object3DJSON:
    metadata: Metadata
    geometries: List[Geometry]
    materials: List[Material]
    object: Union[ObjectData,GeometryObject]


def find_object_by_uuid(data: Union[ObjectData, GeometryObject], uuid: str) -> Optional[Union[ObjectData, GeometryObject,dict[str, object]]]:
    """
    Recursively searches for an object by its UUID within an ObjectData or GeometryObject hierarchy.

    Args:
        data: The root ObjectData or GeometryObject to search within.
        uuid: The UUID of the object to find.

    Returns:
        The object with the matching UUID, or None if not found.
    """
    # Check if the current object has the matching UUID
    if isinstance(data,dict):

        if data['uuid'] == uuid:
            return data

        # Recursively search in the children
        for child in data.get('children',[]):
            result = find_object_by_uuid(child, uuid)
            if result:
                return result
        return None


    if data.uuid == uuid:
        return data

    # Recursively search in the children
    if data.children is not None:
        for child in data.children:
            result = find_object_by_uuid(child, uuid)
            if result:
                return result

    # If the object was not found in the current node or any children, return None
    return None



def find_object_by_uuid_in_object3d(data: Object3DJSON, uuid: str) -> Optional[Union[ObjectData, GeometryObject]]:
    """
    Finds and returns an object by UUID in the Object3DJSON structure.

    Args:
        data: The root Object3DJSON object.
        uuid: The UUID of the object to find.

    Returns:
        The object with the matching UUID, or None if not found.
    """
    # Start the search from the root object
    if isinstance(data,dict):
        return find_object_by_uuid(data['object'], uuid)
    else:
        return find_object_by_uuid(data.object, uuid)


def update_object_userdata(data, uuid, updates, deleted=()):
    obj=find_object_by_uuid_in_object3d(data,uuid)
    if isinstance(obj,dict):
        ud=obj.get('userData',dict())
        props=ud.get('properties',dict())
        props.update(updates)
        for d in deleted:
            if d in props:

                del props[d]

        ud['properties']=props
        obj['userData']=ud
    else:
        props=obj.userData.properties
        props.update(updates)
        for d in deleted:
            if d in props:
                del props[d]

        obj.userData.properties=props


import numpy as np


def generate_indexes(vertices):
    unique_vertices = []
    indices = []
    vertex_to_index = {}  # Maps vertex to its index

    for vertex in vertices:
        # Convert to tuple for hashing
        vertex_tuple = tuple(vertex)
        if vertex_tuple not in vertex_to_index:
            vertex_to_index[vertex_tuple] = len(unique_vertices)
            unique_vertices.append(vertex)
        indices.append(vertex_to_index[vertex_tuple])

    return np.array(unique_vertices), np.array(indices)



from __future__ import annotations
import dataclasses
from collections import namedtuple
from typing import List, Literal, Tuple, Union

from ifcexport2.mesh import Mesh

IfcFail = namedtuple("IfcFail", ["item", "tb"])
ImportFailList = Union[List, List[IfcFail]]

@dataclasses.dataclass(slots=True,unsafe_hash=True)
class IRGeometryObject:
    id: int
    type: str
    name: str
    context: str
    parent_id: int
    transform: List[float]
    mesh:Mesh
    props:dict[str]= dataclasses.field(default_factory=dict)



@dataclasses.dataclass(slots=True,unsafe_hash=True)
class IRGroupObject:
    id: int
    type: str
    name: str
    props:dict[str]= dataclasses.field(default_factory=dict)
    children:'list[IRGeometryObject|IRGroupObject]'= dataclasses.field(default_factory=list)

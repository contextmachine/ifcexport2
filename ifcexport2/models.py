from __future__ import annotations
import dataclasses
from collections import namedtuple
from typing import List, Literal, Tuple, Union

from ifcexport2.mesh import Mesh

IfcFail = namedtuple("IfcFail", ["item", "tb"])
ImportFailList = Union[List, List[IfcFail]]

@dataclasses.dataclass(slots=True,unsafe_hash=True)
class IRObject:
    id: int
    type: str
    name: str
    context: str
    parent_id: int
    transform: List[float]
    mesh:Mesh
    props:dict[str]= dataclasses.field(default_factory=dict)

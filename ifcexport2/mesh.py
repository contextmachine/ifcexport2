from dataclasses import dataclass,field
import numpy as np
from numpy.typing import NDArray
from typing import Optional

@dataclass(slots=True, unsafe_hash=True)
class Mesh:
    position:NDArray
    faces:Optional[NDArray]=None
    normals:Optional[NDArray]=None
    uv:Optional[NDArray]=None
    colors:Optional[NDArray]=None
    color:Optional[tuple[int,int,int]]=None
    uid:int|str=0


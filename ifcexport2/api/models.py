from __future__ import annotations

import dataclasses
from dataclasses import field

from datetime import timezone, timedelta, datetime

from pydantic import BaseModel
from typing import Literal,Optional

from ifcexport2.ifc_to_mesh import settings_dict

STATUS=Literal['pending','error','success']

class TaskStatus(BaseModel):
    id:str
    status: STATUS
    detail: Optional[str]=None


class ConversionTaskResult(BaseModel):
    name: str
    url: str


greenwich_tz = timezone(timedelta(0), "+00")


def now(tz=None):
    return datetime.now().astimezone(tz)


class ConversionTaskStatus(TaskStatus):
    result: Optional[ConversionTaskResult] = None


@dataclasses.dataclass(slots=True)
class ConversionParamsExtended:
    fp: str
    name: Optional[str] = None
    scale: float = 1.0
    excluded_types: list[str] = field(
        default_factory=lambda: ["IfcSpace", "IfcOpeningElement"]
    )
    settings: dict = dataclasses.field(default_factory=lambda: {**settings_dict})


@dataclasses.dataclass(slots=True, frozen=False)
class ConversionTaskInputs:
    name: Optional[str] = None
    scale: float = 1.0
    excluded_types: list[str] = dataclasses.field(
        default_factory=lambda: ["IfcSpace", "IfcOpeningElement"]
    )
    settings: dict = dataclasses.field(default_factory=lambda: {**settings_dict})


@dataclasses.dataclass(slots=True)
class Upload:
    id: str
    status: Literal["pending", "error", "success"]
    progress: float
    scene_id: int
    user_id: int
    filename: str
    file_path: str
    total_size: int
    created_at: str = field(
        default_factory=lambda: now(greenwich_tz).isoformat(), compare=False
    )
    detail: Optional[str] = None

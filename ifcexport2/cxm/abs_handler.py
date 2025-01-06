from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, runtime_checkable, Protocol
import abc

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class HandlerPostResponse:
    handler: str
    status_code: int
    metadata: Dict[str, Any] = field(default_factory=dict)
@dataclass_json
@dataclass
class HandlerGetResponse:
    handler: str
    status_code: int
    body: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@runtime_checkable
class Handler(Protocol):

    def handle_get(self, url:str)->HandlerGetResponse:...

    def handle_post(self, url: str,data:Dict[str,Any]) -> HandlerPostResponse: ...

    @property
    def next_handler(self)->Handler|None:...




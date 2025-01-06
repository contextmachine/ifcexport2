import uuid
from enum import StrEnum

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from ifcexport2.celery_config import celery_app
from ifcexport2.tasks import ifc_export
from pydantic import BaseModel
from dataclasses import dataclass, asdict
from typing import List, Optional
from pathlib import Path
import json
import os
import asyncio
from fastapi import FastAPI, BackgroundTasks
from celery.result import AsyncResult

import time


import time
import dataclasses
from dataclasses import asdict, is_dataclass, dataclass, field
from typing import Any
import numpy as np
import sys

from starlette.responses import StreamingResponse
from typing_extensions import TypedDict

from ifcexport2.ifc_to_mesh import Mesh, safe_call_fast_convert,IfcFail, ConvertArguments,settings_dict,   convert

from pathlib import Path


import itertools
import tempfile


# Data Models
@dataclass
class IfcObject:
    id: int
    type: str
    name: str

@dataclass
class CollisionCount:
    row: str
    column: str
    value: int

@dataclass
class CollisionDetectionParams:
    critical_depth: float = 1e-3
    eps: float = 1e-4
    scale: float = 1.
    excluded_types: tuple[str] = ("IfcSpace",)


@dataclasses.dataclass
class Collision:
    first: IfcObject
    second: IfcObject
    depth: float
    pt1: tuple[float, float, float]
    pt2: tuple[float, float, float]
@dataclasses.dataclass
class CollisionDetectionResult:
    params: CollisionDetectionParams
    output_file_id: str
    collisions:list[Collision]



@dataclasses.dataclass
class CollisionTableView:
    first_id: int
    second_id: int
    first_name: str
    second_name: str
    first_type: str
    second_type: str
    first_context: str
    second_context: str
    first_parent_id: int
    second_parent_id: int


class UploadTask(BaseModel):
    task_id: str
    url:str="/result"

class UploadTaskStatusEnum(StrEnum):
    processing="processing"
    success="success"

    error="error"


class UploadTaskResult(BaseModel):
    name:str
    endpoint:str

class UploadTaskStatus(BaseModel):
    task_id: str
    status:UploadTaskStatusEnum
    result:Optional[UploadTaskResult]=None
    error:Optional[str]=None





app = FastAPI(
    title="IFC Collision Detection API",
    description="API for processing IFC files, extracting meshes, and detecting collisions.",
    version="1.0.0"
)
# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)


# Global storages
IFCS = dict()
OIFCS=dict()
# TASKS dict will store:
# { task_id: { "status": "pending"|"done"|"error", "result": Optional[list[Collision]] } }
TASKS = {}


# Utility Functions




def proc(contents, data):
    meshes_list = []
    object_lists = []
    fails=[]
    for i,content in enumerate(contents):
        result = safe_call_fast_convert(content, scale=data.scale, excluded_types=data.excluded_types,
                                          threads=max(os.cpu_count() - 2, 1),
                                          settings=settings_dict)

        success, objects, meshes, fails = result.success, result.objects, result.meshes, result.fails
        if success:
            meshes_list.append((i,meshes))
            object_lists.append((i,objects))


@app.post("/upload_ifc")
async def upload_ifc_endpoint(files: list[UploadFile]) -> list[UploadTask]:

    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")

    tasks = []
    for f in files:
        content = await f.read()
        content = content.decode('utf-8')
        task = ifc_export.delay(ConvertArguments(content))
        tasks.append(UploadTask(**{'task_id':task.id, "url":"/result"}))


    return tasks



@app.post("/convert_ifc", response_model=UploadTask)
async def convert_ifc_endpoint(data: ConvertArguments) :
    task = ifc_export.delay(data)
    return UploadTask(**{"task_id":task.id, "url": "/result"})


@app.get("/result/{task_id}",response_model=UploadTaskStatus)
def get_result(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    if result.ready():
        return UploadTaskStatus(**{"task_id": task_id, "status": UploadTaskStatusEnum.success, "result": UploadTaskResult(**result.result)})
    else:
        return UploadTaskStatus(**{"task_id": task_id, "status": UploadTaskStatusEnum.processing})



def check_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    while not result.ready():
        time.sleep(1)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run('app:app', host='0.0.0.0', port=8022, reload=True, log_level='info', access_log=True)

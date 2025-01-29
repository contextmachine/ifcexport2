from __future__ import annotations

import threading
import uuid
from enum import StrEnum


from ifcexport2.tasks import ifc_export


from ifcexport2.celery_config import celery_app

from celery.result import AsyncResult

import time
from ifcexport2.api.app import app


import time
import dataclasses
from dataclasses import asdict, is_dataclass, dataclass, field


from ifcexport2.ifc_to_mesh import settings_dict
from ifcexport2.api.upload import *




class ConversionTaskResult(BaseModel):
    name:str
    url:str

class ConversionTaskStatus(BaseModel):
    id: str
    status:Literal["pending","error","success"]
    result:Optional[ConversionTaskResult]=None
    details:Optional[str]=None





@dataclasses.dataclass(slots=True)
class ConversionParamsExtended:
    fp:str
    name: Optional[str] = None
    scale: float = 1.0
    excluded_types: list[str] = field(default_factory=lambda: ["IfcSpace", "IfcOpeningElement"])
    settings: dict = dataclasses.field(default_factory=lambda: {**settings_dict})


import multiprocessing as mp

@dataclasses.dataclass(slots=True, frozen=False)
class ConversionTaskInputs:
    name: Optional[str] = None
    scale: float = 1.0
    excluded_types: list[str] = dataclasses.field(default_factory=lambda: ["IfcSpace", "IfcOpeningElement"])
    settings: dict = dataclasses.field(default_factory=lambda: {**settings_dict})


@app.post("/conversion/{upload_id}", response_model=ConversionTaskStatus, response_model_exclude_none=True)
async def convert_ifc_endpoint(upload_id:str, data: ConversionTaskInputs) :


    upl=upload_statuses.get(upload_id)

    if upl is None:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    prms = {"fp":upl.file_path, **asdict(data)}
    if prms['name'] is None:
        prms['name']=upl.filename.split('.')[0]

    task = ifc_export.delay(prms)
    return ConversionTaskStatus(**{"id": task.id,"status": "pending"})



@app.get("/conversion/{task_id}",response_model=ConversionTaskStatus, response_model_exclude_none=True)
async def get_result(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        return ConversionTaskStatus(**{"id": task_id, "status": "success", "result": ConversionTaskResult(**result.result)})
    elif result.failed():
        return ConversionTaskStatus(**{"id": task_id, "status": "error", "detail":str(result.traceback)})
    else:
        return ConversionTaskStatus(**{"id": task_id, "status": "pending"})




def check_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    while not result.ready():
        time.sleep(1)

'''      
greenwich_tz=timezone(timedelta(0),'+00')

def now(tz=None):
    return datetime.now().astimezone(tz)

from ifcexport2.settings import UPLOADS_PATH,BLOBS_PATH

from typing import Optional,Any, Literal
import uuid
from fastapi import UploadFile,Request,BackgroundTasks,File,HTTPException
upload_statuses = {}
uploads = {}
from ifcexport2.api.app import app






@dataclasses.dataclass(slots=True)
class UploadProgress:
    id: str
    status: Literal['pending','error','success']

    scene_id:int
    user_id:int
    filename: str
    file_path: str
    total_size:int
    created_at: str=field(default_factory=lambda : now(greenwich_tz).isoformat(),compare=False)
    detail: Optional[str]=None




                       
@app.post("/upload_ifc/{scene_id}/{user_id}")
async def upload_ifc_endpoint(
        scene_id: int,
        user_id: int,
        request: Request,
        file: UploadFile = File(...)
):

    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # 3.1) Figure out total size if we can
    total_size = request.headers.get("content-length")
    try:
        total_size = int(total_size) if total_size else 0
    except ValueError:
        total_size = 0

    # 3.2) Generate an ID for this upload
    upload_id = str(uuid.uuid4())

    # 3.3) Decide final location
    final_path = UPLOADS_PATH/f"{upload_id}.ifc"
    upl=UploadProgress(upload_id,
                     status="pending",
                     scene_id=scene_id,
                     user_id=user_id,
                     total_size=total_size,
                     filename=file.filename,
                     file_path=final_path.__str__()
                     )


    task = file_upload.delay(await file.read(),final_path.__str__() )

    upload_statuses[task.id] = upl

    # 3.4) Spool the incoming upload to a temporary file
    #      So we don't rely on 'file.file' in the background task


    # Initialize the status


    # If we already have some progress, reflect that in the progress calculation



    #background_tasks.add_task(background_upload_task,
    #    upload_id,
    #    final_path,file.file,0)
    # Schedule the background task to continue reading from the file

    return task


@app.get("/upload_status/{task_id}", response_model=UploadProgress)
async def get_upload_status(task_id: str):
    """
    Endpoint to retrieve the current status of the upload by ID.
    """
    status_data = upload_statuses.get(task_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Download ID not found")
    result = AsyncResult(task_id, app=celery_app)
    if result.ready():

        status_data.status="success"
        return status_data
    elif result.failed():

        status_data.status = "error"
        status_data.detail=str(result.traceback)

        return status_data

    return status_data

'''


if __name__ == "__main__":

    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8022, reload=False)

from __future__ import annotations


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

import os
import shutil
from pathlib import Path
from ifcexport2.api.models import TaskStatus, ConversionTaskResult, ConversionTaskStatus, ConversionTaskInputs, Upload
from starlette.concurrency import run_in_threadpool
from ifcexport2.api.redis_helpers import Hset

from ifcexport2.api.settings import UPLOADS_PATH, DEPLOYMENT_NAME

from fastapi import UploadFile, Request, BackgroundTasks, File, HTTPException


import uuid

from ifcexport2.step_decode import step_decode
from ifcexport2.tasks import ifc_export, BLOBS_PATH

from ifcexport2.celery_config import celery_app

from celery.result import AsyncResult

import time
from dataclasses import asdict

upload_statuses = Hset(DEPLOYMENT_NAME + "-uploads")

app = FastAPI(
    title="IFC Exchange API",
    description="API for IFC files processing and exchange",
    version="1.0.0",
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
OIFCS = dict()
# TASKS dict will store:
# { task_id: { "status": "pending"|"done"|"error", "result": Optional[list[Collision]] } }
TASKS = {}


async def background_upload_task(upload_id: str, file_path: str, spooled_path: str):
    upload_data = upload_statuses[upload_id]
    try:
        # 2.1) Check if we need to resume
        total_size = upload_statuses[upload_id].total_size
        existing_offset = 0
        if os.path.exists(file_path):
            existing_offset = os.path.getsize(file_path)
            # If final_path is bigger than total_size (or equals it),
            # we might treat it as done or remove it and restart.
            if existing_offset >= total_size > 0:
                # We'll remove it for the example's sake:
                os.remove(file_path)
                existing_offset = 0

        # 2.2) Open final file in append mode
        with open(file_path, "wb") as out_f:
            # 2.3) Move to "existing_offset" in the spooled file
            with open(spooled_path, "rb") as in_f:

                # skip existing_offset in the spooled file


                out_f.write(step_decode(in_f.read()).encode("utf-8"))

        # done
        upload_data.status = "success"
        upload_statuses[upload_id]=upload_data
    except Exception as exc:
        upload_data.status = "error"
        upload_data.detail = str(exc)
        upload_statuses[upload_id]=upload_data
    Path(spooled_path).unlink()


def cpobj(spooled_path, file):
    with open(spooled_path, "wb") as spool_file:
        # You can do chunked copying if the file is large
        shutil.copyfileobj(file.file, spool_file)


@app.post("/upload", response_model=TaskStatus, response_model_exclude_none=True)
async def upload_ifc_endpoint(
    scene_id: int,
    user_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
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
    final_path = UPLOADS_PATH / f"{upload_id}.ifc"

    upl = Upload(
        upload_id,
        status="pending",
        progress=0.0,
        scene_id=scene_id,
        user_id=user_id,
        total_size=total_size,
        filename=file.filename,
        file_path=final_path.__str__(),
    )
    upload_statuses[upload_id] = upl

    # 3.4) Spool the incoming upload to a temporary file
    #      So we don't rely on 'file.file' in the background task
    spooled_path = UPLOADS_PATH / f"spool_{upload_id}.tmp"

    try:
        await run_in_threadpool(cpobj, spooled_path, file)
        # Copy the entire stream from 'UploadFile' into the spool file

    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Failed to spool file: {str(ex)}")

    # Initialize the status

    # If we already have some progress, reflect that in the progress calculation

    # Schedule the background task to continue reading from the file
    background_tasks.add_task(
        background_upload_task, upload_id, final_path, spooled_path
    )
    return TaskStatus(**{"id": upload_id, "status": "pending"})


@app.get(
    "/upload/{upload_id}", response_model=TaskStatus, response_model_exclude_none=True
)
async def get_upload_status(upload_id: str):
    """
    Endpoint to retrieve the current status of the upload by ID.
    """
    status_data = upload_statuses.get(upload_id)

    if not status_data:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    return TaskStatus(
        **{"id": upload_id, "status": status_data.status, "detail": status_data.detail}
    )


@app.post(
    "/conversion/{upload_id}",
    response_model=ConversionTaskStatus,
    response_model_exclude_none=True,
)
async def convert_ifc_endpoint(upload_id: str, data: ConversionTaskInputs):
    upl = upload_statuses.get(upload_id)

    if upl is None:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    prms = {"fp": upl.file_path, **asdict(data)}
    if prms["name"] is None:
        prms["name"] = upl.filename.split(".")[0]

    prms["upload_id"]=upload_id
    threads: int = max(1, os.cpu_count()-4)

    prms['threads']=threads
    prms['settings']['use-python-opencascade']=False

    task = ifc_export.delay(prms)
    _id = str(task.id)
    del task
    return ConversionTaskStatus(**{"id": _id, "status": "pending"})


@app.get("/blobs/{blob_id}")
async def blobs_proxy(blob_id:str):
    path=BLOBS_PATH/blob_id
    if path.exists() and path.is_file():
        return FileResponse(path)
    else:
        raise HTTPException(status_code=404, detail=f"Blob {blob_id} is not found")





@app.get(
    "/conversion/{task_id}",
    response_model=ConversionTaskStatus,
    response_model_exclude_none=True,
)
async def get_result(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    print(task_id,result.as_tuple())
    if result.successful():
        return ConversionTaskStatus(
            **{
                "id": task_id,
                "status": "success",
                "result": ConversionTaskResult(**result.result),
            }
        )
    elif result.failed():
        tb=str(result.traceback)

        result.forget()

        return ConversionTaskStatus(
            **{"id": task_id, "status": "error", "detail": tb}
        )

    else:
        return ConversionTaskStatus(**{"id": task_id, "status": "pending", "detail":result.status})


def check_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    while not result.ready():
        time.sleep(1)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8022, reload=False)

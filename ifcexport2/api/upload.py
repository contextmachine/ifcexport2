import dataclasses
import os
import shutil
import time
from dataclasses import field
from datetime import datetime,timezone,timedelta,tzinfo
from pathlib import Path

from starlette.concurrency import run_in_threadpool

greenwich_tz=timezone(timedelta(0),'+00')

def now(tz=None):
    return datetime.now().astimezone(tz)

from ifcexport2.settings import UPLOADS_PATH,BLOBS_PATH
import fastapi
from pydantic import BaseModel
from typing import Optional,Any, Literal
import uuid
from fastapi import UploadFile,Request,BackgroundTasks,File,HTTPException,Query
upload_statuses = {}
uploads = {}
from ifcexport2.api.app import app







@dataclasses.dataclass(slots=True)
class UploadProgress:
    id: str
    status: Literal['pending','error','success']
    progress: float
    scene_id:int
    user_id:int
    filename: str
    file_path: str
    total_size: int
    created_at: str=field(default_factory=lambda : now(greenwich_tz).isoformat(),compare=False)
    detail: Optional[str]=None





class UploadTaskResult(BaseModel):
    id:str
    status: Literal['pending','error','success']
    detail: Optional[str]=None


async def background_upload_task(
        upload_id: str,
        file_path: str,
        spooled_path:str



):
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
        with open(file_path, "ab") as out_f:
            # 2.3) Move to "existing_offset" in the spooled file
            with open(spooled_path, "rb") as in_f:
                # skip existing_offset in the spooled file
                in_f.seek(existing_offset)

                bytes_written = existing_offset
                chunk_size = 1024 * 1024  # 1MB

                while True:
                    chunk = in_f.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    bytes_written += len(chunk)

                    # update progress
                    if total_size > 0:
                        percent = round((bytes_written / total_size) * 100, 2)
                    else:
                        # if unknown total_size, treat as done or estimate
                        percent = 100

                    upload_statuses[upload_id].progress = percent

        # done
        upload_statuses[upload_id].status = "success"

    except Exception as exc:
        upload_statuses[upload_id].status= "error"
        upload_statuses[upload_id].detail = str(exc)
    Path(spooled_path).unlink()
def cpobj(spooled_path,file):
    with open(spooled_path, "wb") as spool_file:
        # You can do chunked copying if the file is large
        shutil.copyfileobj(file.file, spool_file)


@app.post("/upload", response_model=UploadTaskResult,response_model_exclude_none=True)
async def upload_ifc_endpoint(
        scene_id: int,
        user_id: int,
        request: Request,
        background_tasks: BackgroundTasks,
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
                     progress= 0.0,
                     scene_id=scene_id,
                     user_id=user_id,
                     total_size=total_size,
                     filename=file.filename,
                     file_path=final_path.__str__()
                     )
    upload_statuses[upload_id]=upl

    # 3.4) Spool the incoming upload to a temporary file
    #      So we don't rely on 'file.file' in the background task
    spooled_path = UPLOADS_PATH/f"spool_{upload_id}.tmp"

    try:
        await run_in_threadpool(cpobj, spooled_path,file)
        # Copy the entire stream from 'UploadFile' into the spool file

    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to spool file: {str(ex)}"
        )

    # Initialize the status


    # If we already have some progress, reflect that in the progress calculation


    # Schedule the background task to continue reading from the file
    background_tasks.add_task(
        background_upload_task,
        upload_id,
        final_path,
        spooled_path

    )
    return  UploadTaskResult(**{"id":upload_id, "status":"pending"})


@app.get("/upload/{upload_id}", response_model=UploadTaskResult,response_model_exclude_none=True)
async def get_upload_status(upload_id: str):
    """
    Endpoint to retrieve the current status of the upload by ID.
    """
    status_data = upload_statuses.get(upload_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    return UploadTaskResult(**{"id":upload_id, "status":status_data.status, "detail":status_data.detail})

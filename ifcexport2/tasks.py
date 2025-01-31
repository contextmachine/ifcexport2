

import gc
import os

import ujson


from .celery_config import celery_app
import time
from ifcexport2.ifc_to_mesh import safe_call_fast_convert, create_viewer_object
from pathlib import Path

VOLUME_PATH=Path(os.getenv("VOLUME_PATH", "./vol")).absolute()
if not VOLUME_PATH.exists():
    raise OSError(f"VOLUME_PATH ({VOLUME_PATH}) is not exists!")


BUCKET_PREFIX=os.getenv("BUCKET_PREFIX",  "http://0.0.0.0:8022")

BLOBS_PATH=Path(os.getenv("BLOBS_PATH", VOLUME_PATH/"blobs")).absolute()

if not BLOBS_PATH.exists():
    BLOBS_PATH.mkdir(parents=True,exist_ok=False)



@celery_app.task
def complex_calculation(x, y):
    time.sleep(10)  # Simulating a long computation
    return x * y


@celery_app.task
def ifc_export(data:dict):
    dt = data

    with open(data['fp'],'rb' ) as f:
        del dt['fp']

        dt['ifc_string'] =f.read().decode('utf-8')

    upload_id=dt.pop("upload_id")

    result=safe_call_fast_convert(**dt)

    root = create_viewer_object(dt['name'], result.objects)

    key=f'{BUCKET_PREFIX}/{BLOBS_PATH.name}/{dt["name"]}-{upload_id}.json'
    with open(BLOBS_PATH/f'{dt["name"]}-{upload_id}.json',"w") as f:
        ujson.dump(root,f)



    name=dt['name']
    del dt
    del data
    del root
    gc.collect()
    return {'url': key,'name': name}


@celery_app.task
def file_upload(data:bytes, path:str):
    path=Path(path)
    if path.parent.exists() and path.is_dir():
        with open(path,'wb') as f:
            f.write(data)

        return {'status': "success",'path':path}

    return {'status': "error", 'path':path,"detail":f"No such directory: {path.parent}"}
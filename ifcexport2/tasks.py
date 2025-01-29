from __future__ import annotations

import dataclasses
from typing import Any, Literal,Optional
import ujson


from .celery_config import celery_app
import time
from ifcexport2.ifc_to_mesh import safe_call_fast_convert, ConvertArguments, create_viewer_object,settings_dict
import multiprocessing as mp
from dataclasses import asdict,field
from pathlib import Path

from .settings import BLOBS_PATH


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


    result=safe_call_fast_convert(**dt)

    root = create_viewer_object(dt['name'], result.objects)
    key=BLOBS_PATH/f'{dt["name"]}.json'
    with open(key,"w") as f:
        ujson.dump(root,f)


    return {'url': key.as_uri(),'name':dt["name"]}


@celery_app.task
def file_upload(data:bytes, path:str):
    path=Path(path)
    if path.parent.exists() and path.is_dir():
        with open(path,'wb') as f:
            f.write(data)

        return {'status': "success",'path':path}

    return {'status': "error", 'path':path,"detail":f"No such directory: {path.parent}"}
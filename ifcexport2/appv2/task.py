


import gc
import os

import ifcopenshell
import ujson




from ifcexport2.ifc_to_mesh import safe_call_fast_convert, create_viewer_object
from pathlib import Path

VOLUME_PATH=Path(os.getenv("VOLUME_PATH", "./vol")).absolute()
if not VOLUME_PATH.exists():
    raise OSError(f"VOLUME_PATH ({VOLUME_PATH}) is not exists!")


BUCKET_PREFIX=os.getenv("BUCKET_PREFIX",  "http://localhost:8022")

BLOBS_PATH=Path(os.getenv("BLOBS_PATH", VOLUME_PATH/"blobs")).absolute()

if not BLOBS_PATH.exists():
    BLOBS_PATH.mkdir(parents=True,exist_ok=False)


def ifc_export(data:dict):
        dt = data
        with open(data['fp'],'rb' ) as f:
            del dt['fp']

            dt['ifc_string'] =f.read().decode('utf-8')

        upload_id=dt.pop("upload_id")

        result=safe_call_fast_convert(**dt)


        root = create_viewer_object(dt['name'], result.objects, ifcopenshell.file.from_string(   dt['ifc_string']),include_spatial_hierarchy=True)

        key=f'{BUCKET_PREFIX}/{BLOBS_PATH.name}/{dt["name"]}-{upload_id}.json'
        with open(BLOBS_PATH/f'{dt["name"]}-{upload_id}.json',"w") as f:
            ujson.dump(root,f)

        name=dt['name']
        del dt
        del data
        del root
        gc.collect()


        return {'url':key,'name': name}




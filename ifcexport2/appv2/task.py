


import gc
import os
from typing import Optional

import ifcopenshell
import ujson

from ifcexport2.cxm.metric_manager import MetricManager
from ifcexport2.ifc_to_mesh import safe_call_fast_convert, create_viewer_object, settings_dict, ConvertArguments, \
        convert
from pathlib import Path

VOLUME_PATH=Path(os.getenv("VOLUME_PATH", "./vol")).absolute()
if not VOLUME_PATH.exists():
    raise OSError(f"VOLUME_PATH ({VOLUME_PATH}) is not exists!")


BUCKET_PREFIX=os.getenv("BUCKET_PREFIX",  "http://localhost:8022")

BLOBS_PATH=Path(os.getenv("BLOBS_PATH", VOLUME_PATH/"blobs")).absolute()

if not BLOBS_PATH.exists():
    BLOBS_PATH.mkdir(parents=True,exist_ok=False)


def ifc_export(data:dict, metric_manager:Optional[MetricManager]=None):
        dt = data
        #if data.get('is_file_path',False):
        #    with open(data['fp'],'rb' ) as f:
        #        del dt['fp']
        #
        #        dt['ifc_string'] =f.read().decode('utf-8')
        #else:

        upload_id=dt.pop("upload_id")



        print(f'from fp: { dt["fp"]}')

        ifc_file=ifcopenshell.open( dt['fp'])

        print(f'success')
        result=convert(
                ConvertArguments(ifc_file, scale=dt['scale'], excluded_types=dt['excluded_types'], threads=dt['threads'],
                                 settings=dt['settings'], name=dt['name']))

        print('convert success')
        root = create_viewer_object(dt['name'], result.objects, ifc_file,include_spatial_hierarchy=False)

        key=f'{BUCKET_PREFIX}/{BLOBS_PATH.name}/{dt["name"]}-{upload_id}.json'
        with open(BLOBS_PATH/f'{dt["name"]}-{upload_id}.json',"w") as f:
            ujson.dump(root,f)

        name=dt['name']
        del dt
        del data
        del root
        del ifc_file
        del result
        gc.collect()
        


        return {'url':key,'name': name}




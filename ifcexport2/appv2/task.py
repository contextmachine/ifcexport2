import dataclasses
import gc
import os
from dataclasses import asdict
from typing import Optional, TypedDict, Any

import ifcopenshell
import ujson
import multiprocessing as mp
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

@dataclasses.dataclass
class IfcExportExtras:
    excluded_types: list[str]= dataclasses.field(default_factory=lambda :list(('IfcSpace',)))
    target_units:Optional[str]=None
    


class IfcExportExtrasData(TypedDict):
    excluded_types: Optional[list[str]]
    target_units:Optional[str]


class ResultData(TypedDict):
    url: str
    name: str
    extras: dict


class TaskData(TypedDict):
    upload_id: str
    status: str
    extras: IfcExportExtrasData
    fp: str
    fname: str
    detail: Optional[str]
    result: Optional[ResultData]

 
  


def ifc_export(data:TaskData,*,volume_path='./vol',blobs_prefix:str='blobs',metric_manager: Optional[MetricManager]=None, threads=None, settings:dict[str,Any]=None)->ResultData:
        dt = data
        #if data.get('is_file_path',False):
        #    with open(data['fp'],'rb' ) as f:
        #        del dt['fp']
        #
        #        dt['ifc_string'] =f.read().decode('utf-8')
        #else:
        if settings is None:
            settings={**settings_dict}
        upload_id=dt["upload_id"]
        name=Path(dt['fname']).stem
        extras:IfcExportExtrasData=IfcExportExtrasData(**dt.get('extras',{}))
        excluded_types=extras.get('excluded_types',[])
        target_units=extras.get('target_units',None)
        if volume_path is not None:
            fp=(Path(volume_path)/ dt["fp"]   ).absolute().__str__()
        else:
            fp=dt["fp"]
        print(f'from fp: {fp}')
        
        ifc_file=ifcopenshell.open( fp)

        print(f'success')
        result=convert( ifc_file,
                ConvertArguments(
                    excluded_types=excluded_types,
                    target_units=target_units,
                    name=name
                ),
                        settings=settings,
                        threads=threads,
                        verbose=True
                        )
        blob_path=Path(volume_path)/blobs_prefix/f'{name}-{upload_id}.json'
        
        blob_url_path=blob_path.absolute().relative_to(
            Path(volume_path).absolute()
        )
        f'{BUCKET_PREFIX}/{blob_url_path.__str__()}'
        print('convert success')
        root = create_viewer_object(name, result.objects, ifc_file,include_spatial_hierarchy=False)
        ud=root['object'].get('userData',{})
        props=ud.get('properties',{})
        props['units']=result.info.units.symbol
       
        ud['properties']=props
        root['object']['userData']=ud
        
        
        key= f'{BUCKET_PREFIX}/{blob_url_path.__str__()}'
        with open(blob_path,mode="w",encoding='utf-8') as f:
            ujson.dump(root,f, ensure_ascii=False)

      
        del dt
        del data
        del root
        del ifc_file
        del result
        gc.collect()
        


        return {'url':key,'name': name, 'extras':extras}




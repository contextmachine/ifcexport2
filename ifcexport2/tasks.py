from typing import Any

from .celery_config import celery_app
import time
from ifcexport2.ifc_to_mesh import safe_call_fast_convert, ConvertArguments, create_viewer_object
from dataclasses import asdict

from .cxm.consts import AWS_ENDPOINT_URL, AWS_DEFAULT_BUCKET
from .cxm.s3 import S3Storage, S3Bucket


@celery_app.task
def complex_calculation(x, y):
    time.sleep(10)  # Simulating a long computation
    return x * y

s3 = S3Storage()

bucket: S3Bucket = s3.get_client(AWS_ENDPOINT_URL, True).get_bucket(AWS_DEFAULT_BUCKET)
views = []
@celery_app.task
def ifc_export(data:ConvertArguments):

    result=safe_call_fast_convert(**asdict(data))

    root = create_viewer_object(data.name, result.objects)
    key=f'uploads/{data.name}.json',
    res=bucket.post(key, root)
    print(res)

    return {'endpoint': bucket.get_url(key),'name':data.name}

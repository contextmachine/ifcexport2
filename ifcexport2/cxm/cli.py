import os
from dataclasses import asdict

import click
import termcolor
from fastapi import FastAPI
from typing import Annotated

from fastapi import Body

from  ifcexport2.cxm.handlers import DefaultHandler,S3Handler
from  ifcexport2.cxm.models import *
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from  ifcexport2.cxm.tools.props_update import server_side_props_update

chain_of_responsibility = S3Handler(
    DefaultHandler()
)
app = FastAPI(title="contextmachine props server",
              description="Provides common functionality for updating and deleting properties in frontend representations of CXM cloud models.")
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/props-update")
async def props_update(data:Annotated[UpdatePropsBody,Body( examples=[
    {
        "scene_id": 123,
        "user_id": 123,
        "model_id": 123,
        "endpoint": {
            "type": "rest",
            "entry": "link",
            "query": "http://storage.yandexcloud.net/lahta.contextmachine.online/files/ptcloud%2Bmesg.json"
        },
        "props_data": {
            "object_uuids": [
                "87b31171-5001-4247-a5fa-c72546e6270c"
            ],
            "updated_props": {
                "key1": "value",
                "key2": "value",
            },
            "deleted_props": [
                "name"
            ]
        }
    }
            ],)]):
    """
    Inputs:
    ------

    **data**: Contains the information needed to update cloud properties including endpoint query, object UUIDs, and properties to be updated or deleted.

    Example:

        {
            "scene_id": 123,
            "user_id": 123,
            "model_id": 123,
            "endpoint": {
                "type": "rest",
                "entry": "link",
                "query": "http://storage.yandexcloud.net/lahta.contextmachine.online/files/ptcloud%2Bmesg.json"
            },
            "props_data": {
                "object_uuids": [
                    "87b31171-5001-4247-a5fa-c72546e6270c"
                ],
                "updated_props": {
                    "key1": "value",
                    "key2": "value",
                },
                "deleted_props": [
                    "name"
                ]
            }
        }

    ---

    **return**: The response after updating the object user data and posting to the endpoint.

    Example:

        {
          "handler": "S3Handler",
          "status_code": 200,
          "metadata": {
            "ResponseMetadata": {
              "RequestId": "b0fd712871174bf9",
              "HostId": "",
              "HTTPStatusCode": 200,
              "HTTPHeaders": {
                "server": "nginx",
                "date": "Tue, 17 Sep 2024 21:36:58 GMT",
                "content-type": "application/json",
                "transfer-encoding": "chunked",
                "connection": "keep-alive",
                "keep-alive": "timeout=60",
                "etag": "\"dac2944bed08bf92f27d887f6018cdba\"",
                "vary": "Origin, Access-Control-Request-Headers, Access-Control-Request-Method",
                "x-amz-request-id": "b0fd712871174bf9",
                "x-amz-version-id": "000622577D395286"
              },
              "RetryAttempts": 0
            },
            "ETag": "\"dac2944bed08bf92f27d887f6018cdba\"",
            "VersionId": "000622577D395286"
          }
        }

    """
    try:
        response= server_side_props_update(data, chain_of_responsibility)
    except NotImplementedError as err:
        return JSONResponse(status_code=422, content={"reason": f"Could not find handler for passed query url: '{data.endpoint.query}'"})

    return JSONResponse(status_code=response.status_code, content=asdict(response))
@click.group(name='cxmmt')
@click.help_option('--help', '-h', help='Show this message and exit.')
def cxmmt():
    pass
import uvicorn

@cxmmt.command('props-server')
@click.option("--host",default=os.getenv('CXM_HOST', "0.0.0.0") )
@click.option("--port",default=int(os.getenv('CXM_PORT',7712)) )
@click.option("--root-path",default=os.getenv('CXM_ROOT_PATH','') )
@click.option("--use-ssl",is_flag=True,default=False )
@click.help_option('--help', '-h', help='Show this message and exit.')
def props_server(host,port,root_path,use_ssl=False):
    _rp='"'+root_path + '"'

    print(termcolor.colored('INFO',"green")
          + f":     Options: [host={termcolor.colored(host, 'cyan')}, "
            f"port={termcolor.colored(port, 'cyan')}, "
            f"root_path={termcolor.colored( _rp, 'cyan')}, "
            f"use_ssl={termcolor.colored( use_ssl, 'cyan')}]."
          )

    print(termcolor.colored('INFO', "green")
          + f":     OpenAPI UI (local): http://127.0.0.1:{port}{root_path}/docs\n")

    os.environ['CXM_USE_SSL'] = str(int(use_ssl))

    uvicorn.run('cxm_model_tools.cli:app',host=host,port=port, root_path=root_path)


if __name__ == "__main__":



    print(os.environ)
    cxmmt()

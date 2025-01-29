from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from multipledispatch import dispatch
from dataclasses import asdict

import requests

from  ifcexport2.cxm.abs_handler import Handler,HandlerPostResponse
from  ifcexport2.cxm.models import UpdatePropsBody, update_object_userdata, PropsData, Endpoint,ObjectData
from  ifcexport2.cxm.handlers import DefaultHandler,S3Handler
def flattenObject3D(obj:dict[str]):
    if obj.get('children',[]):
        for child in obj['children']:
            yield from flattenObject3D(child)
    else:
        yield obj

def get_object(url):
    return requests.get(url).json()['object']

def server_side_props_update(data:UpdatePropsBody, handler:Handler):
    """
    :param data: Contains the information needed to update cloud properties including endpoint query, object UUIDs, and properties to be updated or deleted.
    :return: The response after updating the object user data and posting to the endpoint.
    """
    resp=handler.handle_get(data.endpoint.query)
    for i in data.props_data.object_uuids:

        update_object_userdata(resp.body,i, data.props_data.updated_props,data.props_data.deleted_props)
    res=handler.handle_post(data.endpoint.query, resp.body)
    return res
@dispatch(UpdatePropsBody)
def client_side_props_update(data:UpdatePropsBody)->HandlerPostResponse:
    """
    Sends a POST request to update client-side properties and returns the
    server response as a HandlerPostResponse object. This function utilizes
    the information provided in the data object to make a POST request to a
    specified endpoint with the data converted to a JSON format.

    :param data: Contains the endpoint information and data to be sent.
    :type data: UpdatePropsBody
    :return: The parsed response from the server after posting the update.
    :rtype: HandlerPostResponse
    """


    resp=requests.post( data.endpoint.entry,json=data.to_dict())

    return HandlerPostResponse.from_json(resp.text)

@dispatch(str,PropsData)
def  client_side_props_update(url:str,props_data:PropsData):
    return client_side_props_update(UpdatePropsBody(**{"scene_id": 0, "user_id": 0, "model_id": 0},props_data=props_data,
    endpoint = Endpoint('rest', "https://props-server.dev.contextmachine.cloud/props-update",
                        url)))
@dispatch(str,list,dict)
def  client_side_props_update(url:str,uuids:list[str], update_props:dict):
    return client_side_props_update(UpdatePropsBody(**{"scene_id": 0, "user_id": 0, "model_id": 0},props_data=PropsData(uuids,update_props,[]),
    endpoint = Endpoint('rest', "https://props-server.dev.contextmachine.cloud/props-update",
                        url)))



from datetime import datetime

def _generate_update_queries(current_objects, object_uuids,key='collision'):
    updated_props={}
    deleted_props =[]
    current_time = datetime.now().isoformat('YY-MM-DD' )

    # Identify objects to activate/update and deactivate
    to_activate = set(object_uuids)
    to_deactivate = set(current_objects.keys()) - to_activate

    # Query 1: Activate and update objects
    query_activate = {
        "object_uuids": list(to_activate),
        "updated_props": {**updated_props, key: True},
        "deleted_props": deleted_props
    }

    # Query 2: Deactivate objects
    query_deactivate = {
        "object_uuids": list(to_deactivate),
        "updated_props": {key: current_time},
        "deleted_props": list(updated_props.keys())  # Remove updated properties
    }

    return query_activate, query_deactivate
import requests
@lru_cache(maxsize=None)
def _get_objects_props(url):



    return {obj['uuid']:obj.get('userData',dict()).get('properties',dict()) for obj in flattenObject3D(requests.get(url).json()['object']
                                                                                                       )}


def apply_tag(get_url: str, post_url: str, key: str, objects_ixs: list):
    current = _get_objects_props(get_url)

    if isinstance(objects_ixs[0], int):
        objects_uuids: list[str] = []

        l = list(current.keys())
        for i in objects_ixs:
            objects_uuids.append(l[i])
    elif isinstance(objects_ixs[0], str):
        objects_uuids: list[str] = objects_ixs
    else:
        raise ValueError(f"Unknown object indices type {objects_ixs}")

    upd, deact = _generate_update_queries(current, objects_uuids, key)

    resp = requests.post(post_url, json=UpdatePropsBody(**{"scene_id": 0, "user_id": 0, "model_id": 0},
                                                        props_data=PropsData.from_dict(upd),
                                                        endpoint=Endpoint('rest', post_url,
                                                                          get_url)).to_dict())
    print(resp.text)
    if resp.status_code == 200:

        resp = requests.post(post_url, json=UpdatePropsBody(**{"scene_id": 0, "user_id": 0, "model_id": 0},
                                                            props_data=PropsData.from_dict(deact),
                                                            endpoint=Endpoint('rest', post_url,
                                                                              get_url)).to_dict())
        print(resp.text)
        return resp
    else:
        resp.raise_for_status()

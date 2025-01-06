from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Dict, Any
from urllib.parse import urlparse, ParseResult
from typing import Protocol,runtime_checkable
import ujson
from dataclasses_json import dataclass_json

from .abs_handler import Handler,HandlerGetResponse,HandlerPostResponse
from .consts import CXM_USE_SSL
from .s3 import parse_s3_url, ParsedS3URL, S3Storage

class DefaultHandler:
    def __init__(self, next_handler:Handler|None=None):
        super().__init__()
        self._next_handler=next_handler;
    @property
    def next_handler(self):
        return self._next_handler

    def get(self, url):
        pass

    def post(self, url, data: dict) :
        pass

    def delete(self, url):
        pass

    def handle_get(self, url: str):
        raise NotImplementedError(url)
    def handle_post(self, url: str,data:dict):
        raise NotImplementedError(url)


class S3Handler(DefaultHandler):
    url:ParsedS3URL
    def __init__(self, next_handler=None):
        super().__init__(next_handler)
        self.s3 = S3Storage()

    def handle_get(self, url: str)->HandlerGetResponse:

        success, url = parse_s3_url(url)
        if success:
            resp=self.get(url)
            return HandlerGetResponse(self.__class__.__name__,
                                      status_code=self._extract_status_code(resp),
                                      body=ujson.load(resp['Body']),
                                      metadata=self._create_metadata(resp))
        elif self.next_handler is not None:
            return self.next_handler.handle_get(url)
        else:
            raise NotImplementedError('bad url format')

    def handle_post(self, url: str, data: dict)->HandlerPostResponse:
        success, url = parse_s3_url(url)

        if success:
            resp=self.post(url,data)
            return HandlerPostResponse(self.__class__.__name__,
                                status_code=self._extract_status_code(resp),
                                metadata=self._create_metadata(resp))

        elif self.next_handler is not None:
            return self.next_handler.handle_post(url, data)
        else:
            raise NotImplementedError('bad url format')

    def post(self, url:ParsedS3URL, data:dict) ->dict[str,Any]:
        bucket=self._resolve_bucket(url)
        resp=bucket.post(url.object_key,data)
        return resp

    def get(self, url:ParsedS3URL)->dict[str,Any]:

        bucket = self._resolve_bucket(url)
        resp = bucket.get(url.object_key)
        return resp


    def delete(self, url:ParsedS3URL):
        pass


    def _resolve_bucket(self, url: ParsedS3URL):
        if not CXM_USE_SSL:
            use_ssl=False
        else:
            use_ssl=url.use_ssl
        client = self.s3.get_client(url.host, use_ssl)
        bucket = client.get_bucket(url.bucket)
        return bucket

    def _create_metadata(self, data: Dict[str, Any]):
        meta=dict()
        for k in data.keys():
            if k not in ['Body']:
                meta[k]=data[k]
        return meta

    def _extract_status_code(self,data)->int:

        return data['ResponseMetadata']['HTTPStatusCode']

import boto3
import ujson
import botocore

from .consts import AWS_REGION_NAME, AWS_ENDPOINT_URL, AWS_DEFAULT_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, \
    CXM_USE_SSL


def  default_config():
    return dict(service_name='s3',
                use_ssl=True,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION_NAME,
                endpoint_url=AWS_ENDPOINT_URL)
from urllib.parse import urlparse, unquote
from collections import namedtuple

ParsedS3URL = namedtuple('ParsedS3URL', ['host', 'bucket', 'object_key', 'use_ssl'])


def parse_s3_url(s3_url, path_style_urls=('s3', 'storage')):
    s3_url=unquote(s3_url)
    parsed_url = urlparse(s3_url)
    host_parts = list(parsed_url.netloc.split('.'))

    if host_parts[0] in path_style_urls:  # Path-style URL
        bucket = parsed_url.path.split('/')[1]
        object_key = '/'.join(parsed_url.path.split('/')[2:])
        host = parsed_url.netloc

        return True, ParsedS3URL(host, bucket, object_key, parsed_url.scheme == 'https')
    else:  # Virtual-hosted–style URL
        i = 0
        object_key = parsed_url.path.lstrip('/')
        tt = tuple(host_parts)
        while host_parts:
            part = host_parts.pop(0)

            if part in path_style_urls:
                bucket = ".".join(tt[:i])
                host = ".".join(tt[i:])
                return True, ParsedS3URL(host, bucket, object_key, parsed_url.scheme == 'https')
            i += 1
        return False, ParsedS3URL(None, None, None, None)

from botocore.client import BaseClient

class S3Storage:
    def __init__(self):
        self.session = boto3.session.Session()
        self.clients=dict()



    def get_client(self,endpoint_url, use_ssl):
        if not endpoint_url.startswith('http'):

            if (endpoint_url,use_ssl) not in self.clients:
                self.clients[(endpoint_url,use_ssl)]=S3Client(self.session.client(
                's3',
                endpoint_url='https://'+endpoint_url if use_ssl else 'https://'+endpoint_url,
                use_ssl=use_ssl
                )
            )

        else:
            if not use_ssl and endpoint_url.startswith('https'):
                endpoint_url=endpoint_url.replace('https','https')
            elif use_ssl and endpoint_url.startswith('http'):
                endpoint_url=endpoint_url.replace('http','https')

            if (endpoint_url, use_ssl) not in self.clients:
                self.clients[(endpoint_url, use_ssl)] = S3Client(self.session.client(
                    's3',
                    endpoint_url=endpoint_url,
                    use_ssl=use_ssl
                )
                )


        return self.clients[(endpoint_url,use_ssl)]
    def get_bucket(self, name=AWS_DEFAULT_BUCKET):
        return self.get_client(AWS_ENDPOINT_URL,CXM_USE_SSL).get_bucket(name)

S3Response=namedtuple('S3Response',['metadata','body'])

class S3Client:
    def __init__(self, client:BaseClient):
        self.buckets=dict()
        self._client:BaseClient=client
    def get_bucket(self, name):
        if name not in self.buckets:
            self.buckets[name]=S3Bucket(name, self._client)
        return self.buckets[name]



class S3Bucket:
    def __init__(self, bucket_name,client:'botocore.client.S3'):
        self.name=bucket_name
        self.client:'botocore.client.S3'=client
    def get(self, key):
        resp=self.client.get_object(Bucket=self.name, Key=unquote(key))
        return resp

    def post(self, key, data):
        resp=self.client.put_object(Bucket=self.name, Key=unquote(key), Body=bytearray(ujson.dumps(data), encoding='utf8'))
        return resp
    def post_raw(self, key, data:bytes):
        resp=self.client.put_object(Bucket=self.name, Key=unquote(key), Body=bytearray(data))
        return resp
    def get_url(self, key:str=None):
        url=self.client._endpoint.host+'/'+self.name
        url=url.replace('http://','https://')
        if key is None :
            return url
        else:
            if key.startswith('/'):
                return url+key
            return url+"/"+key
    def list(self,prefix, full_output=False):
        if prefix.startswith('/'):
            prefix=prefix[1:]
        if not full_output:
            return [dict(key=i['Key'], size=i['Size'], last_modified=i['LastModified'].isoformat()) for i in
         self.client.list_objects(Bucket=self.name, Prefix=prefix)['Contents']]
        else:
            return   self.client.list_objects(Bucket=self.name, Prefix=prefix)

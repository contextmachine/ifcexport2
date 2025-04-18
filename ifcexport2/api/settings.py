import os
from collections import namedtuple
from pathlib import Path
import redis
VOLUME_PATH=Path(os.getenv("VOLUME_PATH", "./vol")).absolute()
if not VOLUME_PATH.exists():
    raise OSError(f"VOLUME_PATH ({VOLUME_PATH}) is not exists!")

UPLOADS_PATH=Path(os.getenv("UPLOADS_PATH", VOLUME_PATH/"uploads")).absolute()
BUCKET_PREFIX=os.getenv("BUCKET_PREFIX")

BLOBS_PATH=Path(os.getenv("BLOBS_PATH", VOLUME_PATH/"blobs")).absolute()
if not UPLOADS_PATH.exists():
    UPLOADS_PATH.mkdir(parents=True,exist_ok=False)
if not BLOBS_PATH.exists():
    BLOBS_PATH.mkdir(parents=True,exist_ok=False)

REDIS_URL=os.getenv("REDIS_URL", 'redis://localhost:6379/0')
ParsedHost=namedtuple("ParsedHost", ['host','port'])
def hostparse(netloc:str):
    host,port=netloc.split(':')
    return ParsedHost(host,int(port))
from urllib.parse import urlparse
redis_url=urlparse(REDIS_URL)
redis_host,redis_port=hostparse(redis_url.netloc)

redis_client=redis.Redis(redis_host,redis_port,redis_url.path[1:])

IS_IN_KUBER=bool(os.getenv('KUBERNETES_PORT', False))

def extract_deployment_name(pod_name: str) -> str:
    if IS_IN_KUBER:
        parts = pod_name.split('-')
        if len(parts) < 3:
            raise ValueError("Invalid pod name format")
        return '-'.join(parts[:-2])  # Exclude the last two parts
    else:
        return pod_name

DEPLOYMENT_NAME="ifc-export"



consumer_settings=dict(
    max_attempts_count=2
)
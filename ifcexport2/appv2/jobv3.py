# consumer.py
import multiprocessing
import os
from collections import namedtuple

import rich
import ujson

from ifcexport2.api.settings import DEPLOYMENT_NAME,consumer_settings
from redis import Redis
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError
from redis.retry import Retry

VOLUME_PATH=os.getenv('VOLUME_PATH','./vol')
# exponential back-off: 1s, 2s, 4s … capped at 10 s, max 6 tries
retry_cfg = Retry(
    ExponentialBackoff(cap=10, base=1),
    retries=10
)
REDIS_URL = os.getenv("REDIS_URL", 'redis://localhost:6379/0')
ParsedRedisHost = namedtuple("ParsedHost", ['host', 'port','db'])

from urllib.parse import urlparse

def redis_urlparse(redis_url: str):
    
    redis_url_parsed=urlparse(redis_url)
    if redis_url_parsed.scheme not in ('redis','valkey'):
        raise ValueError(f"Invalid redis url: {redis_url}")
    
    host, port = redis_url_parsed.hostname,redis_url_parsed.port
    try:
        if redis_url_parsed.path in (None,'','/'):
            db=0
        else:
            db=int(redis_url_parsed.path[1:])
        
    except Exception as err:
        raise ValueError(f"Invalid db format: {redis_url_parsed.path}") from err
    return ParsedRedisHost(host, port, db)


from urllib.parse import urlparse


REDIS_HOST, REDIS_PORT, REDIS_DB= redis_urlparse(REDIS_URL)
REDIS_PASSWORD=os.getenv("REDIS_PASSWORD",None)
NUM_THREADS=int(os.getenv("NUM_THREADS",str(multiprocessing.cpu_count()-1)))

def from_redis( data: dict):
    
    return {k: ujson.loads(v) for k, v in data.items()}


def to_redis(data: dict):
    return {k: ujson.dumps(v,ensure_ascii=False) for k, v in data.items()}
def get_task(task_id: str):

    return from_redis(redis_client.hgetall(task_id))


def set_task(task_id:str,task: dict):
    
    return bool(redis_client.hset(task_id, mapping=to_redis(task)
                                  )
                )

if __name__ =='__main__':
    import json
    

    from ifcexport2.appv2.task import ifc_export, ResultData, TaskData
    
    redis_client=redis_conn = Redis(host=REDIS_HOST,
                       port=REDIS_PORT,
                       password=REDIS_PASSWORD,
                       db=REDIS_DB,
                       health_check_interval=30,
                       socket_keepalive=True,
                       max_connections=50,
                       # socket_connect_timeout=5,  # fail fast on cold start
                       # socket_timeout=5,
              
                       retry=retry_cfg,
                       retry_on_error=[ConnectionError, TimeoutError],
                       decode_responses=True
                       
                       )
    redis_client_raw=redis_conn_raw = Redis(host=REDIS_HOST,
                          port=REDIS_PORT,
                          password=REDIS_PASSWORD,
                          db=0,
                          
                          # socket_connect_timeout=5,  # fail fast on cold start
                          # socket_timeout=5,
                          
                          decode_responses=False
                          
                          )

    
    # Initialize Redis
    r = redis_client

    from ifcexport2.cxm.metric_manager import MetricManager, exception_data



    # BRPOP will block until there is an item in "task_queue".
    # It returns a tuple: (queue_name, item)
    # where 'item' is the JSON we initially pushed.
    redis_queue=f"{DEPLOYMENT_NAME}-task-queue"
    if int(redis_client.llen(redis_queue))==0:
        exit(0)
    
    task_id = redis_client.brpoplpush(redis_queue, f"{DEPLOYMENT_NAME}:tasks:processing", 0)
    print(task_id)
    attempts = 0
    # queue_data is something like: (b'task_queue', b'{"task_id":"...","data":"..."}')
    if task_id:
        task_item =  get_task(task_id)
        rich.print(task_item)
     

        print(f"Consumer picked up task {task_id} with data: {task_item}")

    else:
        print(f"NO TASK ID {task_id} ")
        raise ValueError(f"NO TASK ID {task_id} ")
    
    try:
        #metric_manager.update_app_context({'status':'work', 'task_id':task_id})
        from ifcexport2.settings import settings
        result=  ifc_export(task_item,volume_path=VOLUME_PATH,blobs_prefix='blobs',threads=NUM_THREADS,settings=settings,metric_manager=None)
        
        task_item['result']=result
        task_item['status']='success'
 
        # Update the Redis hash with success
    
        redis_conn.hset(task_id,mapping=to_redis(task_item))
    
        print(f"Task {task_id} successfully completed: {result}")
    
    
    except OSError as err:
            print(f"Task {task_id} failed with os error: {err}")
            task_item['status']='error'
            task_item['detail']=exception_data(err)
      
            redis_conn.hset(task_id,mapping=to_redis(task_item))
            


    
            

            raise err
    except Exception as err:
            print(f"Task {task_id} failed with error: {err}")
            task_item['status'] = 'error'
            task_item['detail'] = exception_data(err)
            # In case of any error, update Redis with error status
            redis_conn.hset(task_id, mapping=to_redis(task_item))
    
    

            

            raise err




    print("Job completed.")


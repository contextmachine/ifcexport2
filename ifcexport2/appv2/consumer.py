# consumer.py
import json
import os
import threading
import time
from dataclasses import asdict
from typing import TypedDict, Optional, Literal

import redis
import gc

from ifcexport2.api.settings import DEPLOYMENT_NAME,consumer_settings
from ifcexport2.api.redis_helpers import redis_client
from ifcexport2.appv2.task import ifc_export
from ifcexport2.appv2.consumer_stats import process_stats
# Initialize Redis
r = redis_client

# Create a pubsub instance and subscribe to "tasks"

print("Consumer is running and listening for tasks...")
import redis
import traceback
class ExceptionData(TypedDict):
    type:str
    args:list[Optional[str]]
    traceback:str
    attempts:int

def exception_data(exc:Exception)->ExceptionData:


    full_error = traceback.format_exc()
    print("Captured traceback:\n", full_error)

    return {'type':exc.__class__.__name__,'args':[str(arg) for arg in exc.args],'traceback':full_error}
    # full_error is now a normal str — log it, send it, test it, etc.
def get_hashes_with_field(r: redis.Redis, field: str, match="*", count=1_000):
    """
    Returns a dict mapping each hash‑key that contains `field`
    to its value for that field.
    """
    cursor = 0
    result = {}
    while True:
        # scan for hash‑type keys in batches
        cursor, keys = r.scan(
            cursor=cursor,
            match=match,
            count=count,
            _type="hash"      # requires redis-py ≥4.4 and Redis ≥6.0
        )
        if not keys and cursor == 0:
            break

        # pipeline the HEXISTS + HGET calls for efficiency
        pipe = r.pipeline()
        for k in keys:
            pipe.hexists(k, field)
        exists = pipe.execute()

        pipe = r.pipeline()
        for k, has in zip(keys, exists):
            if has:
                pipe.hget(k, field)
        values = pipe.execute()

        # collect results (only where HEXISTS was true)
        for k, has, val in zip(keys, exists, values):
            if has:
                result[k.decode()] = val.decode()

        if cursor == 0:
            break

    return result
stack=[]

if not r.hexists('ifc-export-consumers','num'):
    r.hset('ifc-export-consumers', mapping={"num":0})
    num=0

else:
    num=int(r.hget('ifc-export-consumers', "num"))+1
    r.hset('ifc-export-consumers', "num", num)
app_name=f'ifc-export-consumer-{num}'

r.hkeys(app_name)
def update_consumer_info(status:Literal['idle','work','error','stop']='idle',current_task:str=None):
    r.hset(app_name,mapping={ 'status': status,'stats': json.dumps(asdict(process_stats())), 'last_update':time.time()})
    if current_task is not None:
        r.hset(app_name,'current_task',current_task )
def update_consumer_exit_info():

    r.hset(app_name,'exit','true')
if __name__ =='__main__':
    import threading as th


    thrdd=dict(stop_th=False)

    def ww():
        global stop_th

        while True:

            if thrdd['stop_th'] :
                print('thstop')
                break

            update_consumer_info(

            )

            time.sleep(0.25)


    thr=threading.Thread(target=ww)
    thr.start()

    print('app name:',app_name)
    while True:

        # BRPOP will block until there is an item in "task_queue".
        # It returns a tuple: (queue_name, item)
        # where 'item' is the JSON we initially pushed.

        queue_data = r.brpop(f"{DEPLOYMENT_NAME}_task_queue")  # or (queue, item) = r.brpop(["task_queue"])
        attempts = 0
        # queue_data is something like: (b'task_queue', b'{"task_id":"...","data":"..."}')
        if queue_data:
            _, raw_item = queue_data
            task_item = json.loads(raw_item)

            task_id = task_item["task_id"]
            task_data = task_item["data"]

            print(f"Consumer picked up task {task_id} with data: {task_data}")


        try:
                update_consumer_info('work', current_task=task_id)

                result =   ujson.dumps(ifc_export(task_data))

                # Update the Redis hash with success
                r.hset(task_id, mapping={
                    "status": "success",
                    "result": result,
                    "data": json.dumps(task_data),
                    "detail": ""

                })
                gc.collect()
                update_consumer_info('idle')
                print(f"Task {task_id} completed successfully.")


        except KeyboardInterrupt as err:
            thrdd['stop_th'] = True
            thr.join(1.)
            r.hset(task_id, mapping={
                "status": "error",
                "result": "",
                "data": json.dumps(task_data),
                "detail": exception_data(err),
                "attempts": attempts + 1
            })
            thrdd['stop_th'] = True
            thr.join(1.)
            update_consumer_info('stop')

            update_consumer_exit_info()
            raise err


        except OSError as err:

                r.hset(task_id, mapping={
                    "status": "error",
                    "result": "",
                    "data": json.dumps(task_data),
                    "detail": json.dumps( exception_data(err)),
                    "attempts":attempts+1
                })
                thrdd['stop_th']=True
                thr.join(1.)
                update_consumer_info('error',current_task=task_id)

                gc.collect()

                update_consumer_exit_info()
                raise err
        except Exception as err:

                # In case of any error, update Redis with error status
                r.hset(task_id, mapping={
                    "status": "error",
                    "result": "",
                    "data": json.dumps(task_data),
                    "detail":json.dumps(exception_data(err)),
                    "attempts":attempts+1
                })

                print(f"Task {task_id} failed with error: {err}")
                update_consumer_info('idle')
                gc.collect()
        gc.collect()
        time.sleep(1)

    thrdd['stop_th'] = True
    thr.join(1.)
    print("Consumer is stopped...")
    update_consumer_exit_info()

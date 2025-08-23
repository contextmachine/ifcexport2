# consumer.py

from ifcexport2.api.settings import DEPLOYMENT_NAME,consumer_settings

if __name__ =='__main__':
    import json

    from ifcexport2.api.redis_helpers import redis_client
    from ifcexport2.appv2.task import ifc_export

    # Initialize Redis
    r = redis_client

    from ifcexport2.cxm.metric_manager import MetricManager, exception_data


    with MetricManager(redis_client, f'{DEPLOYMENT_NAME}:jobs') as metric_manager:
        # BRPOP will block until there is an item in "task_queue".
        # It returns a tuple: (queue_name, item)
        # where 'item' is the JSON we initially pushed.
        if int(redis_client.llen(f"{DEPLOYMENT_NAME}_task_queue"))==0:
            exit(0)
        
        queue_data = redis_client.brpoplpush(f"{DEPLOYMENT_NAME}_task_queue", f"{DEPLOYMENT_NAME}:tasks:processing", 0)
        print(queue_data)
        attempts = 0
        # queue_data is something like: (b'task_queue', b'{"task_id":"...","data":"..."}')
        if queue_data:
            raw_item = queue_data
            task_item = json.loads(raw_item)

            task_id = task_item["task_id"]
            task_data = task_item["data"]

            print(f"Consumer picked up task {task_id} with data: {task_data}")


        try:
            metric_manager.update_app_context({'status':'work', 'task_id':task_id})

            result =   json.dumps(ifc_export(task_data,metric_manager=metric_manager))

            # Update the Redis hash with success
            r.hset(task_id, mapping={
                    "status": "success",
                    "result": result,
                    "data": json.dumps(task_data),
                    "detail": ""

                })






        except OSError as err:

                r.hset(task_id, mapping={
                    "status": "error",
                    "result": "",
                    "data": raw_item,
                    "detail": json.dumps( exception_data(err)),

                })

                raise err
        except Exception as err:

                # In case of any error, update Redis with error status
                r.hset(task_id, mapping={
                    "status": "error",
                    "result": "",
                    "data": raw_item,
                    "detail": json.dumps(exception_data(err)),

                })

                print(f"Task {task_id} failed with error: {err}")

                raise err




    print("Job completed.")


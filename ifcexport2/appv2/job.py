# consumer.py
import logging
from ifcexport2.appv2._logging import ColourFormatter
from ifcexport2.api.settings import DEPLOYMENT_NAME
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colour": {
            "()": "qr_tracker_backend._logging.ColourFormatter",  # dotted path to class
            "format": ColourFormatter.FMT_WITH_FP,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colour",
            "level": "INFO",
        }
    },
    "loggers": {
        f"{DEPLOYMENT_NAME}": {  # your library / module
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
LOGLEVEL=logging.INFO



def get_job_name(task_id):
    return f'{DEPLOYMENT_NAME}:jobs:{task_id}'

if __name__ =='__main__':
    import json
    

    from ifcexport2.api.redis_helpers import redis_client
    from ifcexport2.appv2.task import ifc_export

    # Initialize Redis
    r = redis_client

    from ifcexport2.cxm.metric_manager import MetricManager, exception_data
    logger = logging.getLogger(DEPLOYMENT_NAME)
    logger.setLevel(LOGLEVEL)
    logger.info(json.dumps({'status':'idle', 'task_id':None}))
    
    # BRPOP will block until there is an item in "task_queue".
    # It returns a tuple: (queue_name, item)
    # where 'item' is the JSON we initially pushed.
    
    queue_data = redis_client.brpoplpush(f"{DEPLOYMENT_NAME}_task_queue", f"{DEPLOYMENT_NAME}:tasks:processing", 0)
    
    print(queue_data)
    attempts = 0
    # queue_data is something like: (b'task_queue', b'{"task_id":"...","data":"..."}')
    if queue_data:
        raw_item = queue_data
        task_item = json.loads(raw_item)
        
        task_id = task_item["task_id"]
        task_data = task_item["data"]
        logger.info(f"Consumer picked up task {task_id} with data: {task_data}")
     
    
        with MetricManager(redis_client, f'{DEPLOYMENT_NAME}:jobs:{task_id}') as metric_manager:
     
    
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
                logger.info(f"Task {task_id} completed successfully.")
                
            except OSError as err:
    
                    r.hset(task_id, mapping={
                        "status": "error",
                        "result": "",
                        "data": raw_item,
                        "detail": json.dumps( exception_data(err)),
    
                    })
                    logger.critical(f"Task {task_id} failed with system error: {err}")
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
                    logger.error(f"Task {task_id} failed with error: {err}")
                    raise err
    
    logger.info("Job completed.")


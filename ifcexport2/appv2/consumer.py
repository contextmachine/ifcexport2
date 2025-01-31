# consumer.py
import json
import time
import redis

from ifcexport2.api.settings import DEPLOYMENT_NAME
from ifcexport2.appv2.task import ifc_export
# Initialize Redis
r = redis.Redis(host="localhost", port=6379, db=0)

# Create a pubsub instance and subscribe to "tasks"
p = r.pubsub()
p.subscribe("tasks")

print("Consumer is running and listening for tasks...")

while True:
    # BRPOP will block until there is an item in "task_queue".
    # It returns a tuple: (queue_name, item)
    # where 'item' is the JSON we initially pushed.
    queue_data = r.brpop(f"{DEPLOYMENT_NAME}_task_queue")  # or (queue, item) = r.brpop(["task_queue"])

    # queue_data is something like: (b'task_queue', b'{"task_id":"...","data":"..."}')
    if queue_data:
        _, raw_item = queue_data
        task_item = json.loads(raw_item)

        task_id = task_item["task_id"]
        task_data = task_item["data"]

        print(f"Consumer picked up task {task_id} with data: {task_data}")

        # Simulate some work
        try:


            result =   json.dumps(ifc_export(task_data))

            # Update the Redis hash with success
            r.hset(task_id, mapping={
                "status": "success",
                "result": result,
                "detail": ""
            })
            print(f"Task {task_id} completed successfully.")
        except KeyboardInterrupt as err:
            break
        except OSError as err:
            raise err
        except Exception as e:

            # In case of any error, update Redis with error status
            r.hset(task_id, mapping={
                "status": "error",
                "result": "",
                "detail": str(e)
            })
            print(f"Task {task_id} failed with error: {e}")


print("Consumer is stopped...")

import os

from celery import Celery
REDIS_URL=os.getenv("REDIS_URL", 'redis://localhost:6379/0')
celery_app = Celery(
    "worker"

)

celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend =REDIS_URL

celery_app.conf.update(
    result_expires=3600

)

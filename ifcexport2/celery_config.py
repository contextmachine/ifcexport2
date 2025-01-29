from celery import Celery
from ifcexport2.api.settings import REDIS_URL
celery_app = Celery(
    "worker",

)
celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend =REDIS_URL
celery_app.conf.update(
    result_expires=3600*6,
)

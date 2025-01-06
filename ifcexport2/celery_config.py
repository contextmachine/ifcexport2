from celery import Celery

celery_app = Celery(
    "worker",

)
celery_app.conf.broker_url = 'redis://localhost:6379/0'
celery_app.conf.update(
    result_expires=3600,
)

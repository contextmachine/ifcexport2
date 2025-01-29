docker run -p 6379:6379 redis
celery -A ifcexport2.tasks worker &>celery.log
python -m ifcexport2.api

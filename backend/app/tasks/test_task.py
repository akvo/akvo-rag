import time

from app.celery_app import celery_app

@celery_app.task(name="tasks.add")
def add(x, y):
    time.sleep(10)
    return x + y

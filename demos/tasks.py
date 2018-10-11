import os
import time
from datetime import datetime

from celery import Celery


celery_app = Celery("tasks", broker="amqp://")
celery_app.conf.CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'amqp')


@celery_app.task
def add(x, y):
    return int(x) + int(y)


@celery_app.task
def sleep(seconds):
    time.sleep(float(seconds))
    return seconds


@celery_app.task
def echo(msg, timestamp=False):
    return "%s: %s" % (datetime.now(), msg) if timestamp else msg


@celery_app.task
def error(msg):
    raise Exception(msg)


if __name__ == "__main__":
    celery_app.start()

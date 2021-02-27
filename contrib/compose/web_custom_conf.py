ASYNC_TASK = 'CELERY'
CELERY_BROKER_URL = 'amqp://messagebus:5672/myvhost'
# Celery worker settings
CELERY_TASK_IGNORE_RESULT = True

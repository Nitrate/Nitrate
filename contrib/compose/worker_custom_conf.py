ASYNC_TASK = 'CELERY'
CELERY_BROKER_URL = 'amqp://messagebus:5672/myvhost'
# Celery worker settings
CELERY_TASK_IGNORE_RESULT = True
EMAIL_HOST = 'smtp.localhost'
EMAIL_FROM = 'noreply@example.com'

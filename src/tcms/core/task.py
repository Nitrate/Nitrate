# -*- coding: utf-8 -*-

import enum
import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)


@enum.unique
class AsyncTask(enum.Enum):
    """Type names of asynchronous task"""

    DISABLED = "DISABLED"
    THREADING = "THREADING"
    CELERY = "CELERY"


if settings.ASYNC_TASK not in [item.value for item in AsyncTask]:  # pragma: no cover
    raise ValueError(f"Unknown async task type {settings.ASYNC_TASK}")


class Task:
    """Proxy of an asynchronous task"""

    def __init__(self, target):
        if settings.ASYNC_TASK == AsyncTask.CELERY.value:
            try:
                import celery
            except ImportError:
                raise ImportError(
                    "Async task is enabled and set to use celery, but it is not installed."
                )
            self.target = celery.shared_task(target)
        else:
            self.target = target

    def __call__(self, *args, **kwargs):
        if settings.ASYNC_TASK == AsyncTask.DISABLED.value:
            return self.target(*args, **kwargs)
        elif settings.ASYNC_TASK == AsyncTask.THREADING.value:
            thread = threading.Thread(target=self.target, args=args, kwargs=kwargs)
            thread.daemon = True
            thread.start()
        elif settings.ASYNC_TASK == AsyncTask.CELERY.value:
            return self.target.delay(*args, **kwargs)
        else:
            logger.warning(
                "Unknown ASYNC_TASK: %s. Don't know how to run %s.",
                settings.ASYNC_TASK,
                self.target,
            )

import os
from logging.config import dictConfig

from .settings import LOG_PREFIX

CELERYD_HIJACK_ROOT_LOGGER = False
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'request_pushuser_filter': {
            '()': 'pybarker.django.utils.log.RequestPushUserFilter',
        },
    },
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(module)s:%(lineno)s] [%(user)s] %(message)s',
            'datefmt': '%d.%m.%Y %H:%M:%S',
        },
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[%(server_time)s] %(message)s',
        },
        "simple": {
            "format": "[%(asctime)s.%(msecs)03d] %(message)s",
            "datefmt": "%d.%m.%Y %H:%M:%S",
        },
    },
    'handlers': {
        'console': {
            'filters': ['require_debug_true', 'request_pushuser_filter'],
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
        "logfile_ws_trace": {
            "filters": [],
            "class": "logging.handlers.WatchedFileHandler",
            "filename": os.path.join(LOG_PREFIX, "app-ws.log"),
            "formatter": "simple",
        },
        'mail_admins': {
            'level': 'ERROR',  # чтобы на мыло не падала всякая фигня типа 404 итд
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'django.server': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
        'logfile': {
            'filters': ['request_pushuser_filter'],
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(LOG_PREFIX, 'app-logfile.log'),
            'formatter': 'standard',
        },
        'logfile_erp': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(LOG_PREFIX, 'app-erp.log'),
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['console', 'logfile'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db': {
            'handlers': ['null'],
            'propagate': False,
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'DEBUG',
            'propagate': False,
        },
        "ws_trace": {
            "handlers": ["logfile_ws_trace"],
            "level": "DEBUG",
            "propagate": False,
        },
        'py.warnings': {
            'handlers': ['console', 'logfile'],
            'level': 'WARNING',
            'propagate': False,
        },
        'erp_task_logger': {
            'handlers': ['logfile_erp'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
CELERY_TASK_ANNOTATIONS = {
    "ops.tasks.task_sync_erp": {"logger": "erp_task_logger"},
}

dictConfig(LOGGING)

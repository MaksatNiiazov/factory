import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
# чтобы psycopg в дебаг не ругался и пытался только эту имплементацию
os.environ.setdefault('PSYCOPG_IMPL', 'binary')

app = Celery('project')

# Using a string here means the worker will not have to pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

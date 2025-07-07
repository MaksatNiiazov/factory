"""
Настройки проекта для тестирования

В settings.py есть некоторые настройки которые при тестировании не работают или работают медленно.

Здесь они отключены.
"""

from .settings import *

DATABASES['default']['ATOMIC_REQUESTS'] = True

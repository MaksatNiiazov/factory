import redis
import time

from django.conf import settings

import pickle

rediscon = redis.Redis.from_url(url=settings.APP_REDIS_CONNECTION)


# кладёт объект в хранилище, или удаляет если передано None
# timeout - таймаут в секундах, по умолчанию - год
def object_to_redis(key, val, timeout=None):
    if val is not None:
        p_val = pickle.dumps(val, protocol=2)
        rediscon.setex(name=key, value=p_val, time=timeout or 3600 * 24 * 365)
    else:
        rediscon.delete(key)


# получает объект из хранилища, или None если его нет
def object_from_redis(key):
    p_val = rediscon.get(key)
    val = pickle.loads(p_val) if p_val is not None else None
    return val


def redis_form_store(cachekey, data, initial):
    if data:
        object_to_redis(cachekey, data)
    else:
        data = object_from_redis(cachekey) or initial or {}
    return data


# возвращает (состояние (true/false), текст состояния)
def redis_test():
    try:
        return True, '[OK] dbsize: %s, used mem: %s, ping: %s' % (
        rediscon.dbsize(), rediscon.info()['used_memory_human'], rediscon.echo('PONG'))
    except Exception as e:
        return False, '[ERROR] %s' % (e)


# кладёт по ключу какому-то счётчик, указывается таймаут, чтобы потом посчитать сколько за это время добавлялось там объектов
# например количество соединений вебсокета за последние 60 секунд посчитать - каждое содидение кладёт протухающий счётчик итд

# удаление устаревших, ранее указанного времени
def _counter_trunc_expired(key, time_expired):
    rediscon.zremrangebyscore(key, 0, time_expired)


def redis_inc_counter(key, timeout):
    time_now = time.time()
    rediscon.zadd(key, mapping={time_now: time_now})  # добавляются вида: (b'1552659631.0757813', 1552659631.0757813)
    rediscon.expire(key, 3600)  # сама очередь тоже протухает чтобы не осталась навечно потом
    _counter_trunc_expired(key,
                           time_now - timeout)  # здесь тоже удаляем после добавления, вдруг мы не будем вызывать redis_get_counter и накопится дофига


def redis_get_counter(key, timeout):
    _counter_trunc_expired(key, time.time() - timeout)
    return rediscon.zcount(key, 0, '+inf')


# поставить лок по имени и опционально таймаутом, True - получилось получить лок, False - не получилось
# value - можно задать значение лока (например, хранить там таймауты или что-то типа того)
def lock_set(lockname, expiry=None, value=None):
    key = "rlock:%s" % lockname
    # вернёт True если установилось и None если не установилось (ключ уже был)
    return not not rediscon.set(name=key, value=(value or "!"), nx=True, ex=expiry)


# удалить лок по имени
def lock_del(lockname):
    key = "rlock:%s" % lockname
    rediscon.delete(key)


# получить value лока по имени, если лока нет, то будет None
def lock_get(lockname):
    key = "rlock:%s" % lockname
    return rediscon.get(key)


# проверить наличие лока по имени
def lock_has(lockname):
    return lock_get(lockname) is not None


# удалить все локи
def lock_clear():
    cursor = 0
    while True:
        cursor, keys = rediscon.scan(cursor=cursor, match="rlock:*")
        if keys:
            rediscon.delete(*keys)
        if cursor == 0:
            break

import hashlib
import json
import logging

import autobahn

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

logger_api = logging.getLogger("ws_trace")

GROUP_ALL_CONNECTIONS_NAME = 'all_cons'
GROUP_USER_ID = "user-%d"

EVENT_LOGIN = 'login'


class FakeQueryCookieMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        cookies = {}
        qs = scope["query_string"]
        if qs:
            qs = qs.decode("ascii")
            if qs.startswith("token="):
                qs = qs[6:]
                cookies[settings.SESSION_COOKIE_NAME] = qs
        return await self.inner(dict(scope, cookies=cookies), receive, send)


def _user_serialize(user):
    return {
        'id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'middle_name': user.middle_name,
    }


class WSConsumer(JsonWebsocketConsumer):
    def connect(self):
        # accept connection
        self.accept()

        # join "all connections" group
        async_to_sync(self.channel_layer.group_add)(
            GROUP_ALL_CONNECTIONS_NAME, self.channel_name
        )

        # check auth
        self.user = self.scope['user']
        self._log("connect %s", self.user if self.user else "<NULL>")

        if not self.user or not self.user.is_authenticated:
            self.send_api_error(EVENT_LOGIN, 'not authenticated', close=4401)
            return

        if not self.user.is_active:
            self.send_api_error(EVENT_LOGIN, 'disabled account', close=4401)
            return

        self.send_api(EVENT_LOGIN, {'_': _user_serialize(self.user)})

        # join user group
        async_to_sync(self.channel_layer.group_add)(
            GROUP_USER_ID % self.user.id, self.channel_name
        )

    @classmethod
    def encode_json(cls, content):
        result = json.dumps(content, cls=DjangoJSONEncoder, ensure_ascii=False, indent=None)
        return result

    def disconnect(self, close_code):
        # leave "all connections" group
        async_to_sync(self.channel_layer.group_discard)(
            GROUP_ALL_CONNECTIONS_NAME, self.channel_name
        )
        self._log("disconnect (%s) %s", close_code, self.user if self.user else "<NULL>")
        # leave user group
        if self.user and self.user.id:
            async_to_sync(self.channel_layer.group_discard)(
                GROUP_USER_ID % self.user.id, self.channel_name
            )

    # попытка обойти ошибку "Attempt to send on a closed protocol" отправки в закрытый сокет (нечастая, но бесит)
    # https://github.com/django/channels/issues/1466
    # а перегружено send_json а не общий send потому что в вышестоящем send_json делается super().send() и перегруженный
    # send не работает всё равно придётся оба метода перегружать.
    def send_json(self, content, close=False):
        try:
            super().send(text_data=self.encode_json(content), close=close)
        except autobahn.exception.Disconnected as e:
            self._log("error-disconnected: %r", e)
            self.close()

    # логирование в logger_api, предваряя меткой с неким кодом канала
    def _log(self, msg, *args, **kwargs):
        # оригинальное имя канала сликом стрёмное, сократим до более краткого хеша:
        # specific.5a047cd96f1d45de893dde18cf0e81ec!8a05ced7147b420d99b47010c4645a57
        channel_name = (hashlib.md5(self.channel_name.encode("utf-8")).hexdigest())[-8:]
        user_id = self.user.id if self.user else "?"
        msg = "[%s#%s] %s" % (channel_name, user_id, msg)
        logger_api.debug(msg, *args, **kwargs)

    def receive_json(self, content, **kwargs):
        command_type = content.get('_type', 'no-type')
        self._log("recv %s", command_type)
        if hasattr(self, command_type):
            method = getattr(self, command_type)
            self.send_api(command_type, method(content))
        else:
            self.send_api_error(command_type, 'type ' + command_type + ' not found', close=4403)

    # отправка по протоколу ошибки, {'_type', '_error'}
    def send_api_error(self, command_type, error, close=False):
        ret = {'_type': command_type, '_error': error}
        self._log("send error %s (%s)%s", command_type, error, " [close]" if close else "")
        self.send_json(ret, close=close)

    # отправка по протоколу нормальных данных {'_type', '_data': {}}
    # data должен быть dict-ом, если там толькот один ключ "_" то берётся его содержимое как в api
    def send_api(self, command_type, data=None, close=False):
        ret = {'_type': command_type}
        if data:
            if not isinstance(data, dict):
                raise Exception('send_api data not dict')
            # если в ответе только один ключ и именем '_' то всё содержимое ставим в _data без вложенного ключа, как в api
            if len(data) == 1 and '_' in data:
                data = data['_']
            ret.update({'_data': data})
        self._log("send %s%s", command_type, " [close]" if close else "")
        self.send_json(ret, close=close)

    def ping(self, data):
        return {}

    # событие send.eventtoapi приходит (данные эвента: 'command_type', 'data') - и мы отправляем по API всё это ничего не трогая
    def send_eventtoapi(self, event):
        command_type = event['command_type']
        data = event.get('data', None)
        self.send_api(command_type, data)


channel_layer = get_channel_layer()


# подготовка мессажа для засылания в систему ченнелов, отправляется как сообщение с типом send.eventtoapi
def _make_channel_event_message(command_type, data):
    message = {'type': 'send.eventtoapi', 'command_type': command_type}
    if data:
        message.update({'data': data})
    # здесь сериализуем+десериализуем, ибо по каналам должны передаваться тупые сообщения с нативными типами
    # TODO сделано как говно и костыли, теоретически можно тут оптимизировать без перегонки в текст и обратно
    message = WSConsumer.decode_json(WSConsumer.encode_json(message))
    return message


# отправляет всем channel-сообщение send.eventtoapi, которое внутри рассылает обычные api-эвенты с доп.датой возможно
# в общем случае вероятно не должно использоваться, это мастшабная отправка
# см. send_event_to_users если известны юзеры, send_event_to_app для конкретных заявок
def send_event_to_all(command_type, data=None):
    message = _make_channel_event_message(command_type, data)
    # отправляем окончательно всем
    async_to_sync(channel_layer.group_send)(
        GROUP_ALL_CONNECTIONS_NAME, message
    )


# отправляет сообщение только указанным юзерам
# user_id - id юзера или list/set of id
def send_event_to_users(user_id, command_type, data=None):
    message = _make_channel_event_message(command_type, data)
    if isinstance(user_id, int):
        user_id = [user_id]
    if isinstance(user_id, (list, set)):
        for u_id in user_id:
            async_to_sync(channel_layer.group_send)(
                GROUP_USER_ID % u_id, message
            )
    else:
        raise Exception("user_id error type")

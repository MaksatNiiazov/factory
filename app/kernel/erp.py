import json
import logging
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth

from django.utils.translation import gettext_lazy as _

from constance import config

from ops.choices import ERPSyncLogType

logger = logging.getLogger('erp_task_logger')


class ERPException(Exception):
    pass


class ERPApi:
    def __init__(self, base_url=None, login=None, password=None):
        self.base_url = base_url or config.ERP_BASE_URL
        self.login = login or config.ERP_LOGIN
        self.password = password or config.ERP_PASSWORD

    def validate_config(self):
        if not self.base_url:
            raise ERPException(_('Не указан базовый URL в настройке'))

        if not self.login:
            raise ERPException(_('Не указан логин к системе ERP'))

        if not self.password:
            raise ERPException(_('Не указан пароль к системе ERP'))

    def post(self, url, data):
        auth = HTTPBasicAuth(username=self.login, password=self.password)

        headers = {
            'Host': urlparse(self.base_url).hostname
        }

        response = requests.post(url, data=json.dumps(data), auth=auth, headers=headers, timeout=60)
        return response

    def sync_product(self, *, idwicad, modelslug, art, name, description=None, weight=None, params, erp_sync):
        self.validate_config()

        url = self.base_url + '/products/id'
        data = {
            'idwicad': idwicad,
            'modelslug': modelslug,
            'art': art,
            'name': name,
            'description': description,
            'weight': weight,
            'params': params,
        }
        erp_sync.add_log(ERPSyncLogType.DEBUG, f"Отправляем в {url} данные {data}")
        response = self.post(url, data)
        erp_sync.add_log(ERPSyncLogType.HTTP_REQUEST, data, response.content.decode('utf-8'))

        if response.status_code in (200, 201):
            json_data = response.json()

            if json_data['result']['error']:
                text = json_data['result'].get('text')
                raise ERPException(text)

            return json_data['id']
        else:
            raise ERPException(response.content.decode('utf8'))

    def sync_specifications(self, *, idwicad, iderp, count, structure, erp_sync):
        self.validate_config()

        url = self.base_url + '/specifications/id'
        data = {
            'idwicad': idwicad,
            'iderp': iderp,
            'count': count,
            'structure': structure,
        }
        erp_sync.add_log(ERPSyncLogType.DEBUG, f"Отправляем в {url} данные {data}")
        response = self.post(url, data)
        erp_sync.add_log(ERPSyncLogType.HTTP_REQUEST, data, response.content.decode('utf-8'))

        if response.status_code in (200, 201):
            json_data = response.json()

            if json_data['error']:
                text = json_data.get('text')
                raise ERPException(text)

            return json_data
        else:
            raise ERPException(response.content.decode('utf8'))

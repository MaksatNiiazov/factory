import json

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from constance import config

User = get_user_model()


class CRMAuthBackend(BaseBackend):
    def authenticate(self, request, username, password):
        base_url = config.CRM_API_URL

        if not base_url:
            return None

        headers = {
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                base_url + "auth/login/",
                data=json.dumps({
                    "username": username,
                    "password": password,
                }),
                headers=headers,
            )
        except Exception:
            return None

        if response.status_code != 200:
            return None

        json_data = json.loads(response.content)
        token = json_data["key"]

        headers["Authorization"] = f"Bearer {token}"

        response = requests.get(
            base_url + "auth/user/",
            headers=headers,
        )

        if response.status_code != 200:
            return None

        json_data = json.loads(response.content)
        user = User.objects.filter(status=User.INTERNAL_USER, crm_login=json_data['username']).first()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

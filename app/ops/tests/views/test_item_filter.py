from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from rest_framework.test import APIClient
from rest_framework import status

from ops.models import Item, DetailType, Variant

User = get_user_model()


class TestItemViewSetList(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("item-list")

        self.user = User.objects.create_user(email="testuser@example.com", password="password")

        view_item_permission = Permission.objects.get(codename="view_item")
        self.user.user_permissions.add(view_item_permission)

        self.detail_type = DetailType.objects.create(
            name="Test DetailType", designation="DT1", category=DetailType.DETAIL
        )
        self.variant = Variant.objects.create(
            detail_type=self.detail_type, name="Test Variant"
        )

        self.item1 = Item.objects.create(
            name="Item1", type=self.detail_type, variant=self.variant, parameters={"a": 5}, author=self.user
        )
        self.item2 = Item.objects.create(
            name="Item2", type=self.detail_type, variant=self.variant, parameters={"a": 10}, author=self.user
        )
        self.item3 = Item.objects.create(
            name="Item3", type=self.detail_type, variant=self.variant, parameters={"a": 15}, author=self.user
        )

        login_url = reverse("user-login")
        response = self.client.post(login_url, {"username": "testuser@example.com", "password": "password"})
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed. Response content: {response.content.decode('utf-8')}"
        )
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_list_items(self):
        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Failed to list items. Response content: {response.content.decode('utf-8')}"
        )
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 3)

    def test_filter_parameters_a_lte(self):
        response = self.client.get(self.url, {"parameters.a__lte": 10})
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Filtering items with 'parameters.a__lte' failed. Response content: {response.content.decode('utf-8')}"
        )
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item["parameters"]["a"] <= 10 for item in results))

    def test_filter_parameters_a_gte(self):
        response = self.client.get(self.url, {"parameters.a__gte": 10})
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Filtering items with 'parameters.a__gte' failed. Response content: {response.content.decode('utf-8')}"
        )
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item["parameters"]["a"] >= 10 for item in results))

    def test_filter_parameters_a_exact(self):
        response = self.client.get(self.url, {"parameters.a": 10})
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Filtering items with 'parameters.a' failed. Response content: {response.content.decode('utf-8')}"
        )
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["parameters"]["a"], 10)

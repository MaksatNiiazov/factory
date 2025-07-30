from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from ops.models import Project, ProjectItem, DetailType
from catalog.models import ProductClass, ProductFamily, PipeDiameter


class ShockSelectionTests(APITestCase):
    def setUp(self):
        # Create a test user and authenticate
        login_url = reverse("user-login")
        response = self.client.post(login_url, {"username": "testuser@example.com", "password": "password"})
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed. Response content: {response.content.decode('utf-8')}"
        )
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        # Create a project owned by the test user
        self.project = Project.objects.create(
            owner=self.user,
            number="TestProject1",
            load_unit="kN", move_unit="mm", temperature_unit="C"
        )
        # Assume ProductClass and ProductFamily for SSB are present (e.g., "Гидроамортизаторы" class and SSB family)
        self.product_class = ProductClass.objects.get(name__icontains="амортиз")  # e.g., "Гидроамортизаторы"
        self.product_family = ProductFamily.objects.get(name__icontains="SSB")  # e.g., "SSB"
        # Pipe diameter for 100 mm (DN100)
        self.pipe_diameter = PipeDiameter.objects.filter(dn__dn=100).first()
        self.assertIsNotNone(self.pipe_diameter, "DN100 pipe diameter must exist in fixtures")
        # DetailType for clamps and top mounts (attachment categories)
        self.clamp_type = DetailType.objects.get(name__icontains="Хомуты для амортизатора")  # clamp group A
        self.top_mount_type = DetailType.objects.get(name__icontains="крепления для амортизатор")  # top mount group B


    def test_shock_selection(self):
        a = 1
        b = 1
        return
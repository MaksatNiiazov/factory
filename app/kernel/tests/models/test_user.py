from django.test import TestCase
from django.contrib.auth import get_user_model
from kernel.models import Organization

User = get_user_model()

class UserModelTest(TestCase):

    def setUp(self):
        self.org = Organization.objects.create(name="Тестовая организация")

    def test_create_user(self):
        user = User.objects.create(
            email="test@example.com",
            first_name="Иван",
            last_name="Иванов",
            middle_name="Иванович",
            organization=self.org,
            status=User.INTERNAL_USER
        )

        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "Иван")
        self.assertEqual(user.last_name, "Иванов")
        self.assertEqual(user.middle_name, "Иванович")
        self.assertEqual(user.organization, self.org)
        self.assertEqual(user.status, User.INTERNAL_USER)

    def test_user_display_name(self):
        user = User.objects.create(email="test@example.com", first_name="Иван", last_name="Иванов")
        self.assertEqual(user.display_name, "Иванов Иван")

    def test_user_full_name(self):
        user = User.objects.create(email="test@example.com", first_name="Иван", last_name="Иванов", middle_name="Иванович")
        self.assertEqual(user.full_name, "Иванов Иван Иванович")

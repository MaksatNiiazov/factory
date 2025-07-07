from django.test import TestCase
from django.contrib.auth import get_user_model
from kernel.models import ApiToken

User = get_user_model()

class ApiTokenModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(email="test@example.com", first_name="Иван", last_name="Иванов")

    def test_generate_unique_token(self):
        token = ApiToken.objects.create(user=self.user)

        self.assertIsNotNone(token.token)
        self.assertEqual(len(token.token), 22)
        self.assertTrue(ApiToken.objects.filter(token=token.token).exists())

    def test_api_token_str(self):
        token = ApiToken.objects.create(user=self.user)
        self.assertEqual(str(token), f"{self.user}: {token.token}")

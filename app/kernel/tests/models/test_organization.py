from django.test import TestCase
from kernel.models import Organization

class OrganizationModelTest(TestCase):

    def test_create_organization(self):
        org = Organization.objects.create(
            name="Тестовая организация",
            external_id=12345,
            inn="1234567890",
            kpp="0987654321",
            payment_bank="ТестБанк",
            payment_account="40817810099910000000",
            bik="044525225",
            correspondent_account="30101810400000000225"
        )

        self.assertEqual(org.name, "Тестовая организация")
        self.assertEqual(org.external_id, 12345)
        self.assertEqual(org.inn, "1234567890")
        self.assertEqual(org.kpp, "0987654321")
        self.assertEqual(org.payment_bank, "ТестБанк")
        self.assertEqual(org.payment_account, "40817810099910000000")
        self.assertEqual(org.bik, "044525225")
        self.assertEqual(org.correspondent_account, "30101810400000000225")

    def test_organization_str(self):
        org = Organization.objects.create(name="ООО Ромашка")
        self.assertEqual(str(org), "ООО Ромашка")

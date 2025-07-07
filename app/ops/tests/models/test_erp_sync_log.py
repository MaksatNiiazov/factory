from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

from ops.models import ERPSync, ERPSyncLog, Project, Item, DetailType, Variant
from ops.choices import ERPSyncType, ERPSyncStatus, ERPSyncLogType

User = get_user_model()


class ERPSyncLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="log@test.com", password="password")

        self.detail_type = DetailType.objects.create(
            product_family=None,
            name="Test Detail",
            designation="TD",
            category=DetailType.DETAIL,
            branch_qty=DetailType.BranchQty.ONE,
            default_comment="Default Comment"
        )
        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name="Variant Test",
            marking_template="Test Template"
        )
        self.item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            author=self.user
        )
        self.erp_sync = ERPSync.objects.create(
            author=self.user,
            type=ERPSyncType.ITEM,
            item=self.item,
            status=ERPSyncStatus.PENDING,
            comment="Sync test"
        )

    def test_str_method(self):
        """Проверяем корректное строковое представление лога ERP синхронизации."""
        log_type_value = ERPSyncLogType.choices[0][0]
        log = ERPSyncLog.objects.create(
            erp_sync=self.erp_sync,
            log_type=log_type_value,
            request="Test request",
            response="Test response"
        )
        log_str = str(log)
        self.assertIn("Log", log_str)
        self.assertIn(f"for ERP Sync {self.erp_sync.id}", log_str)
        expected_log_type_display = str(dict(ERPSyncLogType.choices).get(log_type_value))
        self.assertIn(expected_log_type_display, log_str)

    def test_log_creation(self):
        """Проверяем создание лога и его связь с ERP синхронизацией."""
        initial_count = ERPSyncLog.objects.count()
        ERPSyncLog.objects.create(
            erp_sync=self.erp_sync,
            log_type=ERPSyncLogType.choices[0][0],
            request="Request data",
            response="Response data"
        )
        self.assertEqual(ERPSyncLog.objects.count(), initial_count + 1)
        log = ERPSyncLog.objects.last()
        self.assertEqual(log.erp_sync, self.erp_sync)
        self.assertEqual(log.request, "Request data")
        self.assertEqual(log.response, "Response data")

    def test_ordering(self):
        """Проверяем, что логи сортируются по ERP синхронизации и дате создания."""
        log1 = ERPSyncLog.objects.create(
            erp_sync=self.erp_sync,
            log_type=ERPSyncLogType.choices[0][0],
            request="First request",
            response="First response"
        )
        log2 = ERPSyncLog.objects.create(
            erp_sync=self.erp_sync,
            log_type=ERPSyncLogType.choices[0][0],
            request="Second request",
            response="Second response"
        )
        logs = list(ERPSyncLog.objects.filter(erp_sync=self.erp_sync))
        self.assertLessEqual(log1.created_at, log2.created_at)
        sorted_logs = sorted(logs, key=lambda x: x.created_at)
        self.assertEqual(logs, sorted_logs)

from django.contrib.auth import get_user_model
from django.test import TestCase

from ops.choices import ERPSyncType, ERPSyncStatus, ProjectStatus, LoadUnit, MoveUnit, TemperatureUnit
from ops.models import ERPSync, ERPSyncLog, Project, Item, DetailType, Variant

User = get_user_model()


class ERPSyncModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="sync@test.com", password="password")

        self.project = Project.objects.create(
            number="P-100",
            contragent="TestContragent",
            organization=None,
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
            standard=1
        )

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

    def test_get_instance_item(self):
        """Если тип синхронизации ITEM, get_instance должен вернуть объект item."""
        sync = ERPSync.objects.create(
            author=self.user,
            type=ERPSyncType.ITEM,
            item=self.item,
            status=ERPSyncStatus.PENDING
        )
        self.assertEqual(sync.get_instance(), self.item)

    def test_get_instance_project(self):
        """Если тип синхронизации PROJECT, get_instance должен вернуть объект project."""
        sync = ERPSync.objects.create(
            author=self.user,
            type=ERPSyncType.PROJECT,
            project=self.project,
            status=ERPSyncStatus.PENDING
        )
        self.assertEqual(sync.get_instance(), self.project)

    def test_get_instance_id(self):
        """Проверяем, что get_instance_id возвращает правильный идентификатор."""
        sync_item = ERPSync.objects.create(
            author=self.user,
            type=ERPSyncType.ITEM,
            item=self.item,
            status=ERPSyncStatus.PENDING
        )
        self.assertEqual(sync_item.get_instance_id(), self.item.id)

        sync_project = ERPSync.objects.create(
            author=self.user,
            type=ERPSyncType.PROJECT,
            project=self.project,
            status=ERPSyncStatus.PENDING
        )
        self.assertEqual(sync_project.get_instance_id(), self.project.id)

    def test_to_json(self):
        """Метод to_json должен возвращать корректный словарь с данными синхронизации."""
        sync = ERPSync.objects.create(
            author=self.user,
            type=ERPSyncType.ITEM,
            item=self.item,
            status=ERPSyncStatus.PENDING,
            comment="Test Comment"
        )
        json_data = sync.to_json()
        self.assertEqual(json_data['id'], sync.id)
        self.assertEqual(json_data['type'], ERPSyncType.ITEM)
        self.assertEqual(json_data['instance'], self.item.id)
        self.assertEqual(json_data['status'], ERPSyncStatus.PENDING)
        self.assertEqual(json_data['comment'], "Test Comment")

    def test_add_log(self):
        """Метод add_log должен создать новую запись лога с корректными данными."""
        sync = ERPSync.objects.create(
            author=self.user,
            type=ERPSyncType.ITEM,
            item=self.item,
            status=ERPSyncStatus.PENDING
        )
        initial_log_count = ERPSyncLog.objects.count()
        sync.add_log(log_type="test_log", request="dummy request", response="dummy response")
        self.assertEqual(ERPSyncLog.objects.count(), initial_log_count + 1)
        log = ERPSyncLog.objects.last()
        self.assertEqual(log.erp_sync, sync)
        self.assertEqual(log.log_type, "test_log")
        self.assertEqual(log.request, "dummy request")
        self.assertEqual(log.response, "dummy response")

    def test_str(self):
        """Метод __str__ должен возвращать строку, содержащую 'ERP Sync', строковое представление связанного объекта и отображение статуса."""
        sync = ERPSync.objects.create(
            author=self.user,
            type=ERPSyncType.ITEM,
            item=self.item,
            status=ERPSyncStatus.PENDING
        )
        s = str(sync)
        self.assertIn("ERP Sync", s)
        self.assertIn(str(self.item), s)
        self.assertIn(sync.get_status_display(), s)

from django.contrib.auth import get_user_model
from django.test import TestCase

from ops.models import Project, ProjectItem, ProjectItemRevision, Item, DetailType, Variant

User = get_user_model()


class ProjectItemRevisionTest(TestCase):
    def setUp(self):
        """Создаем тестовые объекты перед запуском тестов"""
        self.user = User.objects.create_user(email="testuser@mail.ru", password="testpass")

        self.project = Project.objects.create(
            number="P-001",
            owner=self.user,
            load_unit="kN",
            move_unit="mm",
            temperature_unit="C",
        )

        self.detail_type = DetailType.objects.create(
            name="Test Detail Type",
            designation="TDT",
            category=DetailType.DETAIL
        )

        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name="Test Variant"
        )

        self.item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            author=self.user
        )

        self.project_item = ProjectItem.objects.create(
            project=self.project,
            original_item=self.item,
            position_number=1
        )

    def test_create_project_item_revision(self):
        """Тест создания ревизии ProjectItemRevision"""
        revision = ProjectItemRevision.objects.create(
            project_item=self.project_item,
            revision_item=self.item
        )

        self.assertEqual(revision.project_item, self.project_item)
        self.assertEqual(revision.revision_item, self.item)

    def test_str_representation(self):
        """Тест строкового представления ProjectItemRevision"""
        revision = ProjectItemRevision.objects.create(
            project_item=self.project_item,
            revision_item=self.item
        )

        self.assertEqual(str(revision), f"{self.project_item} (#{revision.id})")

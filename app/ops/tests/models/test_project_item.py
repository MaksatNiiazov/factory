from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from kernel.models import Organization
from ops.choices import ProjectStatus, LoadUnit, MoveUnit, TemperatureUnit
from ops.models import Project, ProjectItem, Item, DetailType, Variant

User = get_user_model()


class ProjectItemModelTest(TestCase):
    def setUp(self):
        """Создаём тестовые данные"""
        self.user = User.objects.create_user(email="testuser@mail.ru", password="testpassword")
        self.organization = Organization.objects.create(name="Test Organization")
        self.project = Project.objects.create(
            number="P-001",
            organization=self.organization,
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        self.detail_type = DetailType.objects.create(
            name="Test DetailType",
            designation="TD001",
            category=DetailType.DETAIL
        )

        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name="Test Variant",
            marking_template="TestTemplate"
        )

        self.item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            author=self.user
        )

        self.item.marking, self.item.marking_errors = self.item.generate_marking()
        self.item.save()

    def test_create_project_item(self):
        """Тест создания объекта ProjectItem"""
        project_item = ProjectItem.objects.create(
            project=self.project,
            position_number=1,
            original_item=self.item,
            customer_marking="CustomMark",
            count=5,
            work_type=ProjectItem.MANUFACTURING,
        )
        self.assertEqual(project_item.project, self.project)
        self.assertEqual(project_item.position_number, 1)
        self.assertEqual(project_item.original_item, self.item)
        self.assertEqual(project_item.customer_marking, "CustomMark")
        self.assertEqual(project_item.count, 5)
        self.assertEqual(project_item.work_type, ProjectItem.MANUFACTURING)

    def test_create_project_item_without_required_fields(self):
        """Тест ошибки при создании ProjectItem без обязательных полей"""
        project_item = ProjectItem(
            project=None,
            position_number=1,
        )
        with self.assertRaises(ValidationError):
            project_item.full_clean()

    def test_inner_marking(self):
        """Тест метода inner_marking"""
        project_item = ProjectItem.objects.create(
            project=self.project,
            position_number=2,
            original_item=self.item,
            count=2,
        )
        self.assertEqual(project_item.inner_marking, self.item.marking)

    def test_display_marking(self):
        """Тест метода display_marking"""
        project_item = ProjectItem.objects.create(
            project=self.project,
            position_number=3,
            original_item=self.item,
            customer_marking="CustomMarking",
            count=2,
        )
        self.assertEqual(project_item.display_marking(), "CustomMarking")

        project_item.customer_marking = None
        self.assertEqual(project_item.display_marking(), self.item.marking)

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

    def test_auto_assign_position(self):
        """
        Тест автоматического присвоения номера позиции при создании ProjectItem
        """
        item1 = ProjectItem.objects.create(project=self.project)
        item2 = ProjectItem.objects.create(project=self.project)
        item3 = ProjectItem.objects.create(project=self.project)

        self.assertEqual(item1.position_number, 1)
        self.assertEqual(item2.position_number, 2)
        self.assertEqual(item3.position_number, 3)

    def test_assign_specific_position_and_shift_others(self):
        """
        Тест присвоения конкретного номера позиции и сдвига других позиций
        """
        item1 = ProjectItem.objects.create(project=self.project, position_number=1)
        item2 = ProjectItem.objects.create(project=self.project, position_number=2)
        item3 = ProjectItem.objects.create(project=self.project, position_number=2)

        positions = list(
            ProjectItem.objects.filter(project=self.project).order_by('position_number').values_list(
                'position_number', flat=True
            )
        )
        self.assertEqual(positions, [1, 2, 3])
        self.assertEqual(item3.position_number, 2)

    def test_explicit_unique_position(self):
        """
        Тест уникальности номера позиции при создании ProjectItem
        """
        ProjectItem.objects.create(project=self.project, position_number=1)
        ProjectItem.objects.create(project=self.project, position_number=2)
        item3 = ProjectItem.objects.create(project=self.project, position_number=4)

        self.assertEqual(item3.position_number, 4)

        all_positions = sorted(
            ProjectItem.objects.filter(project=self.project).values_list('position_number', flat=True)
        )
        self.assertEqual(all_positions, [1, 2, 4])

    def test_update_without_position_change(self):
        """
        Тест обновления ProjectItem без изменения номера позиции
        """
        item1 = ProjectItem.objects.create(project=self.project, position_number=1)
        item2 = ProjectItem.objects.create(project=self.project, position_number=2)

        item2.customer_marking = 'UpdatedMarking'
        item2.save()

        positions = list(
            ProjectItem.objects.filter(project=self.project).order_by('position_number').values_list(
                'position_number', flat=True
            )
        )
        self.assertEqual(positions, [1, 2])

    def test_update_with_position_change(self):
        """
        Тест обновления ProjectItem с изменением номера позиции
        """
        item1 = ProjectItem.objects.create(project=self.project, position_number=1)
        item2 = ProjectItem.objects.create(project=self.project, position_number=2)
        item3 = ProjectItem.objects.create(project=self.project, position_number=3)

        item3.position_number = 1
        item3.save()

        positions = list(
            ProjectItem.objects.filter(project=self.project).order_by('position_number').values_list(
                'position_number', flat=True
            )
        )
        self.assertEqual(positions, [1, 2, 3])

        ordered_ids = list(
            ProjectItem.objects.filter(project=self.project).order_by('position_number').values_list('id', flat=True)
        )
        self.assertEqual(ordered_ids, [item3.id, item1.id, item2.id])

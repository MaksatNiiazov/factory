from django.contrib.auth import get_user_model
from django.test import TestCase

from kernel.models import Organization
from ops.choices import ProjectStatus, LoadUnit, MoveUnit, TemperatureUnit
from ops.models import Project

User = get_user_model()


class ProjectModelTest(TestCase):
    def setUp(self):
        """Создаём тестовые данные"""
        self.user = User.objects.create_user(email="testuser", password="testpassword")
        self.organization = Organization.objects.create(name="Test Organization")

    def test_create_project(self):
        """Тест создания проекта"""
        project = Project.objects.create(
            number="P-001",
            organization=self.organization,
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        self.assertEqual(project.number, "P-001")
        self.assertEqual(project.owner, self.user)
        self.assertEqual(project.organization, self.organization)
        self.assertEqual(project.status, ProjectStatus.DRAFT)

    def test_project_number_unique(self):
        """Тест на уникальность номера проекта"""
        Project.objects.create(
            number="P-001",
            organization=self.organization,
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        with self.assertRaises(Exception):
            Project.objects.create(
                number="P-001",
                organization=self.organization,
                owner=self.user,
                status=ProjectStatus.SENT,
                load_unit=LoadUnit.KN,
                move_unit=MoveUnit.MM,
                temperature_unit=TemperatureUnit.CELSIUS,
            )

    def test_project_status_choices(self):
        """Тест выбора корректного статуса"""
        project = Project.objects.create(
            number="P-002",
            organization=self.organization,
            owner=self.user,
            status=ProjectStatus.SENT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        self.assertIn(project.status, dict(Project.STATUSES))

    def test_project_str_method(self):
        """Тест строкового представления модели"""
        project = Project.objects.create(
            number="P-003",
            organization=self.organization,
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        self.assertEqual(str(project), f"Проект #P-003 пользователя {self.user}")


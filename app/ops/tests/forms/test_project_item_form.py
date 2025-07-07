from django.test import TestCase

from catalog.choices import Standard
from ops.choices import EstimatedState
from ops.forms import ProjectItemForm
from ops.models import ProjectItem, DetailType, Project
from catalog.models import PipeDiameter, Material, NominalDiameter
from django.contrib.auth import get_user_model

User = get_user_model()


class ProjectItemFormTest(TestCase):

    def setUp(self):
        """Создание тестовых данных"""
        self.user = User.objects.create_user(email="test@example.com", password="password123")
        self.project = Project.objects.create(number="P-001", contragent="ООО Тест", owner=self.user)
        self.product_type = DetailType.objects.create(name="Тестовый тип", category=DetailType.PRODUCT,
                                                      branch_qty=DetailType.BranchQty.ONE)

        self.nominal_diameter, _ = NominalDiameter.objects.get_or_create(dn=100)

        self.pipe_diameter = PipeDiameter.objects.create(
            dn=self.nominal_diameter,
            option=PipeDiameter.Option.DN_A,
            standard=Standard.EN,
            size=114.3
        )

        self.material = Material.objects.create(name="Сталь", group="Металлы")

        self.valid_data = {
            'question_list': '',
            'customer_marking': 'ABC-123',
            'count': 5,
            'load_plus_x': 10,
            'load_plus_y': 10,
            'load_plus_z': 10,
            'load_minus_x': 5,
            'load_minus_y': 5,
            'load_minus_z': 5,
            'additional_load_x': 2,
            'additional_load_y': 2,
            'additional_load_z': 2,
            'test_load_x': 1,
            'test_load_y': 1,
            'test_load_z': 1,
            'move_plus_x': 1,
            'move_plus_y': 1,
            'move_plus_z': 1,
            'move_minus_x': 1,
            'move_minus_y': 1,
            'move_minus_z': 1,
            'estimated_state': EstimatedState.COLD_LOAD,
            'ambient_temperature': 20,
            'nominal_diameter': self.pipe_diameter.id,
            'outer_diameter_special': '',
            'insulation_thickness': 5,
            'span': 100,
            'clamp_material': self.material.id,
            'chain_height': 200,
            'tmp_spring': '',
            'position_number': 1,
            'comment': 'Тестовый комментарий',
            'dn_standard': 1,
            'product_type': self.product_type.id
        }

    def test_valid_form(self):
        """Тест с валидными данными"""
        form = ProjectItemForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields(self):
        """Тест пропущенных обязательных полей"""
        invalid_data = self.valid_data.copy()
        invalid_data.pop('dn_standard')
        form = ProjectItemForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('dn_standard', form.errors)

    def test_invalid_product_type(self):
        """Тест с неверным типом изделия"""
        invalid_data = self.valid_data.copy()
        invalid_data['product_type'] = None
        form = ProjectItemForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('product_type', form.errors)

    def test_valid_diameter_standard(self):
        """Тест на корректное использование стандарта диаметра"""
        self.valid_data['dn_standard'] = 2
        form = ProjectItemForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_span_for_two_branch_qty(self):
        """Тест: если у типа изделия 2 отвода, но не указан span"""
        self.product_type.branch_qty = DetailType.BranchQty.TWO
        self.product_type.save()

        invalid_data = self.valid_data.copy()
        invalid_data['span'] = None
        form = ProjectItemForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('span', form.errors)

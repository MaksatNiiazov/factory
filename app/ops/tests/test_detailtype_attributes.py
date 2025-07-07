from django.urls import reverse
from modeltranslation.utils import get_language
from rest_framework import status
from rest_framework.test import APITestCase
from ops.models import DetailType, FieldSet, Variant, Attribute, BaseComposition
from kernel.models import User


class DetailTypeAttributesTestCase(APITestCase):
    """
    Тест-кейс для проверки API доступных атрибутов типа деталей.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Создаёт тестовые данные перед запуском тестов:
        - Создаётся суперпользователь.
        - Создаётся DetailType (Тип детали).
        - Создаётся Variant (Вариант исполнения).
        - Создаётся FieldSet (Группа параметров).
        - Создаются два атрибута (вес и высота).
        - Создаётся BaseComposition (базовый состав).
        - Добавляются атрибуты к base_child.
        """
        cls.user = User.objects.create_superuser(email="testuser@example.com", password="testpass")
        cls.detail_type = DetailType.objects.create(name="Опора DN100", designation="MSN", category="detail")
        cls.variant = Variant.objects.create(detail_type=cls.detail_type, name="Исполнение 1")
        cls.fieldset = FieldSet.objects.create(name="Основные параметры", label="Основные параметры")

        cls.attribute_1 = Attribute.objects.create(
            variant=cls.variant, name="weight", type="number", fieldset=cls.fieldset, position=1
        )
        cls.attribute_2 = Attribute.objects.create(
            variant=cls.variant, name="height", type="number", fieldset=cls.fieldset, position=2
        )

        cls.base_child = DetailType.objects.create(name="Дополнительный элемент", designation="ZOM",
                                                   category="assembly_unit")
        cls.base_composition = BaseComposition.objects.create(
            base_parent=cls.detail_type,
            base_child=cls.base_child,
            position=1,
            count=1
        )

        cls.base_variant = Variant.objects.create(detail_type=cls.base_child, name="Базовое исполнение")
        cls.base_attribute_1 = Attribute.objects.create(
            variant=cls.base_variant, name="base_weight", type="number", fieldset=cls.fieldset, position=1
        )
        cls.base_attribute_2 = Attribute.objects.create(
            variant=cls.base_variant, name="base_height", type="number", fieldset=cls.fieldset, position=2
        )

    def setUp(self):
        """
        Выполняет аутентификацию перед каждым тестом.
        Логинит пользователя и устанавливает токен аутентификации в заголовках.
        """
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.assertEqual(response.status_code, 200, "Ошибка аутентификации: неправильный логин или пароль")

        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_get_available_attributes(self):
        """
        Проверка получения доступных атрибутов для Variant.
        """
        url = reverse('variant-available-attributes', kwargs={'detail_type_pk': self.detail_type.id, 'pk': self.variant.id})
        response = self.client.get(url)

        lang = get_language()  # Получаем текущий язык

        expected_attributes = [
            {"id": self.attribute_1.id, "label": None,
             "name": "weight", "type": "number", "category": "detail",
             "designation": "MSN", "formatted": "detail_MSN.weight"},
            {"id": self.attribute_2.id, "label": None,
             "name": "height", "type": "number", "category": "detail",
             "designation": "MSN", "formatted": "detail_MSN.height"},
        ]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), expected_attributes)

        for attr in expected_attributes:
            self.assertIn(attr, response.data)

    def test_get_available_attributes_invalid_variant(self):
        """
        Проверка, что API вернёт 404, если передан несуществующий variant_id.
        """
        url = reverse('variant-available-attributes', kwargs={
            'detail_type_pk': self.detail_type.id,
            'pk': 999999
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    def test_get_available_attributes_from_base_composition(self):
        """
        Проверка, что API возвращает атрибуты из BaseComposition.
        """
        url = reverse('variant-available-attributes',
                      kwargs={'detail_type_pk': self.detail_type.id, 'pk': self.variant.id})
        response = self.client.get(url)

        formatted_attributes = [attr["formatted"] for attr in response.data]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail_MSN.weight", formatted_attributes[0])
        self.assertIn("detail_MSN.height", formatted_attributes[1])

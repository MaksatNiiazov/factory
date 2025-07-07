import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.test import TestCase
from ops.models import Variant, DetailType
from django.conf import settings


class VariantTestCase(TestCase):
    def setUp(self):
        """Создаем тестовые данные перед каждым тестом"""
        self.detail_type = DetailType.objects.create(
            name="Test Detail Type",
            designation="TD001",
            category=DetailType.DETAIL,
        )
        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name="Variant 1",
            marking_template="VAR-{{ detail_type.designation }}",
        )

    def test_create_variant(self):
        """Тест создания варианта"""
        self.assertEqual(self.variant.name, "Variant 1")
        self.assertEqual(self.variant.detail_type, self.detail_type)





    def _create_test_image(self, width=1024, height=1024):
        """Создает тестовое изображение и возвращает его как `ContentFile`"""
        img = Image.new("RGB", (width, height), "white")
        image_io = BytesIO()
        img.save(image_io, format="JPEG")
        return ContentFile(image_io.getvalue(), name="test_image.jpg")

    def test_soft_delete(self):
        """Тест мягкого удаления (`soft delete`)"""
        # TODO Написать тест для мягкого удаления варианта
        pass

    def test_resize_image(self):
        """Тест уменьшения изображения"""
        # TODO Написать тест для ресайза изображения в варианте
        pass

    def test_generate_sketch(self):
        """Тест генерации эскиза"""
        # TODO Написать тест для генерации скетча в варианте
        pass



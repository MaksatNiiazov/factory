from django.test import TestCase
from django.contrib.auth.models import Group
from kernel.api.serializers import GroupSerializer


class GroupSerializerTest(TestCase):
    def setUp(self):
        """Создаём тестовую группу перед каждым тестом"""
        self.group = Group.objects.create(name="Test Group")

    def test_group_serialization(self):
        """Проверка сериализации группы"""
        serializer = GroupSerializer(instance=self.group)
        data = serializer.data

        self.assertEqual(data["id"], self.group.id)
        self.assertEqual(data["name"], self.group.name)

    def test_group_deserialization(self):
        """Проверка десериализации данных группы"""
        valid_data = {
            "name": "New Group"
        }

        serializer = GroupSerializer(data=valid_data)

        if not serializer.is_valid():
            print(serializer.errors)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

        new_group = serializer.save()
        self.assertEqual(new_group.name, "New Group")

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from ops.choices import AttributeType
from ops.models import DetailType, Variant, Attribute, FieldSet, Item
from ops.tasks import process_import_task
from taskmanager.choices import TaskStatus
from taskmanager.models import Task, TaskAttachment

User = get_user_model()


class DetailTypeAttributesTestCase(APITestCase):
    """
    Тест-кейс для проверки API доступных атрибутов типа деталей.
    """

    def setUp(self):
        self.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')
        login_response = self.client.post(
            '/api/users/login/',
            data={'username': 'testuser@example.com', 'password': 'testpass'},
            format='json',
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.data.get('token')
        self.assertIsNotNone(token)

        self.detail_type, _ = DetailType.objects.get_or_create(
            designation='FHD',
            category='assembly_unit',
            defaults={
                'name': 'Тестовый деталь',
            }
        )
        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name='wil',
        )

        fieldset = FieldSet.objects.create(
            name='general',
        )

        Attribute.objects.create(
            variant=self.variant,
            type=AttributeType.INTEGER,
            name='H',
            fieldset=fieldset,
            position=1,
        )
        Attribute.objects.create(
            variant=self.variant,
            type=AttributeType.INTEGER,
            name='L',
            fieldset=fieldset,
            position=2,
        )

        self.item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            parameters={
                'H': 5,
                'L': 3,
            },
            author=self.user,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_import_csv(self):
        csv_content = f'id,weight,material,variant,H,L\n,,mat,wil,3,5\n,,mat,asd,5,4'
        csv_content = csv_content.encode('utf-8')
        csv_file = SimpleUploadedFile('test.csv', csv_content, content_type='text/csv')

        payload = {
            'type': 'csv',
            'category': 'assembly_unit',
            'designation': 'FHD',
            'file': csv_file,
            'is_dry_run': True,
        }

        response = self.client.post('/api/items/import_data/', data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.content.decode('utf-8'))

        task_id = response.data.get('id')
        self.assertIsNotNone(task_id)

        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, TaskStatus.NEW)

        attachment = TaskAttachment.objects.filter(task=task, slug='imported_file').first()
        self.assertIsNotNone(attachment)

        process_import_task(task.id)

        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, TaskStatus.DONE, msg=task.status_details)

        response = self.client.get(f'/api/tasks/{task.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode('utf-8'))

        data = response.json()
        self.assertEqual(data['status'], TaskStatus.DONE)

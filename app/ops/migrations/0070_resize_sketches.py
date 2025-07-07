from io import BytesIO

from PIL import Image
from django.core.files.base import ContentFile
from django.db import migrations
from django.db.models import Q


def resize_sketches(apps, scheme_editor):
    Variant = apps.get_model('ops', 'Variant')

    variants = Variant.objects.exclude(Q(sketch__isnull=True) | Q(sketch=''))
    max_width = 520
    max_height = 680

    for variant in variants:
        img = Image.open(variant.sketch)

        width, height = img.size
        ratio = width / height

        if width > height and width > max_width:
            new_height = round(max_width / ratio)
            size = (max_width, new_height)
        elif height > width and height > max_height:
            new_width = round(max_height * ratio)
            size = (new_width, max_height)
        else:
            continue

        img = img.resize(size, Image.Resampling.LANCZOS)

        image_io = BytesIO()

        # Устанавливаем формат по умолчанию, если он не определен
        img_format = img.format if img.format else 'JPEG'

        # Проверяем формат, если формат 'JPEG', используем 'RGB' mode
        if img_format == 'JPEG' and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Сохраняем изображение
        img.save(image_io, format=img_format)

        new_image = ContentFile(image_io.getvalue(), name=variant.sketch.name)

        variant.sketch = new_image
        variant.save()


class Migration(migrations.Migration):
    dependencies = [
        ('ops', '0069_variant_sketch_coords'),
    ]

    operations = [
        migrations.RunPython(resize_sketches),
    ]

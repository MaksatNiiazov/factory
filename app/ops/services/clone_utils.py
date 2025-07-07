import os
from django.core.files.base import ContentFile


def get_model_fields_for_clone(model, exclude=None):
    """
    Возвращает список полей модели для клонирования, исключая id и реально существующие системные поля.
    """
    exclude = set(exclude or [])
    all_field_names = [f.name for f in model._meta.get_fields() if f.concrete]
    present_exclude = {field for field in exclude if field in all_field_names}
    return [f for f in all_field_names if f not in {'id'} | present_exclude]


def generate_unique_copy_name(base: str, existing: set, suffix: str = '(Копия)', sep: str = ' ', number_separator=' ') -> str:
    """
    Генерирует уникальное имя с суффиксом и номером:
    - base (Копия)
    - base (Копия 2)
    - или base__copy, base__copy2
    """
    counter = 1
    candidate = f"{base}{sep}{suffix}"
    while candidate in existing:
        counter += 1
        candidate = f"{base}{sep}{suffix}{number_separator}{counter}"
    return candidate

def clone_image_field(image_field, instance):
    """
    Клонирует поле ImageField (если заполнено).
    """
    image = getattr(instance, image_field)
    if not image:
        return None
    with image.open('rb') as f:
        content = ContentFile(f.read())
        content.name = f'copy_{os.path.basename(image.name)}'
        return content

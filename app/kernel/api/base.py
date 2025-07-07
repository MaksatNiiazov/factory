from django.conf import settings
from rest_framework.serializers import Serializer

from rest_framework.utils import model_meta


class ChoicesSerializer(Serializer):
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        field = self.model._meta.get_field(self.field_name)

        choices = field.choices
        verbose_name = next((choice[1] for choice in choices if choice[0] == instance), None)

        return {
            "value": instance,
            "verbose_name": verbose_name,
        }


class TranslatorSerializerMixin:
    """
    Миксин для динамического добавления полей с языками в Serializer
    """
    translated_fields = []

    def get_fields(self):
        fields = super().get_fields()

        if hasattr(self, 'Meta') and hasattr(self.Meta, 'translated_fields'):
            translated_fields = self.Meta.translated_fields
            lang_codes = [lang[0] for lang in settings.LANGUAGES]

            model = getattr(self.Meta, 'model')

            info = model_meta.get_field_info(model)

            for field in translated_fields:
                if field in fields:
                    fields.pop(field)

                    for lang_code in lang_codes:
                        field_name = f'{field}_{lang_code}'

                        field_class, field_kwargs = self.build_field(field_name, info, model, 0)
                        fields[field_name] = field_class(**field_kwargs)

        return fields


class CleanSerializerMixin:
    """
    Миксин, чтобы выполнялся метод full_clean у объекта,
    без ошибки при наличии ManyToMany полей.
    """

    def validate(self, data):
        model_class = self.Meta.model
        m2m_field_names = {
            f.name for f in model_class._meta.get_fields()
            if f.many_to_many and not f.auto_created
        }

        # Копируем и исключаем M2M поля из data
        data_for_model = {k: v for k, v in data.items() if k not in m2m_field_names}

        if self.instance is not None:
            instance = self.instance
            for key, value in data_for_model.items():
                setattr(instance, key, value)
        else:
            instance = model_class(**data_for_model)

        model_fields = set(f.name for f in model_class._meta.get_fields())
        serializer_fields = set(self.Meta.fields)

        excluded_fields = model_fields - serializer_fields

        instance.full_clean(exclude=excluded_fields)

        # Обновляем поля обратно из инстанса (если вдруг были преобразования)
        for field in data_for_model.keys():
            data[field] = getattr(instance, field)

        return super().validate(data)

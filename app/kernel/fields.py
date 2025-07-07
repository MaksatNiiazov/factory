from django import forms
from django.core.exceptions import ValidationError
from django.db import models


class AttributeChoiceFormField(forms.CharField):
    def __init__(self, *, el_type=str, **kwargs):
        self.el_type = el_type
        super().__init__(**kwargs)

    def prepare_value(self, value):
        if isinstance(value, list):
            items = []

            for x in value:
                if x['value'] != x['display_name']:
                    items.append('{}|{}'.format(str(x['value']), str(x['display_name'])))
                else:
                    items.append(str(x['value']))

            return '\n'.join(items)
        return value

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, list):
            items = []

            for item in value:
                if isinstance(item, dict):
                    items.append({
                        'value': self.el_type(item['value']),
                        'display_name': item['display_name'],
                    })
                else:
                    items.append({
                        'value': self.el_type(item),
                        'display_name': str(item),
                    })

            return items

        if not isinstance(value, str):
            raise ValidationError('error value type %s' % type(value))

        value = value.strip()

        if not value:
            return []

        items = []
        try:
            for item in value.splitlines():
                if not item:
                    continue

                if '|' in item:
                    item, display_name = item.split('|')

                    if not item:
                        continue

                    items.append({
                        'value': self.el_type(item),
                        'display_name': display_name,
                    })
                else:
                    items.append({
                        'value': self.el_type(item),
                        'display_name': item,
                    })

            return items
        except Exception as exc:
            raise ValidationError('error comma-separated-%s value "%s"' % (self.el_type.__name__, value))


class AttributeChoiceField(models.TextField):
    def __init__(self, verbose_name=None, name=None, el_type=str, *args, **kwargs):
        self.el_type = el_type
        super().__init__(verbose_name=verbose_name, name=name, *args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.el_type != str:
            kwargs["el_type"] = self.el_type
        return name, path, args, kwargs

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, list):
            items = []

            for item in value:
                if isinstance(item, dict):
                    items.append({
                        'value': self.el_type(item['value']),
                        'display_name': item['display_name'],
                    })
                else:
                    items.append({
                        'value': self.el_type(item),
                        'display_name': str(item),
                    })

            return items

        if not isinstance(value, str):
            raise ValidationError('error value type %s' % type(value))

        value = value.strip()

        if not value:
            return []

        items = []
        try:
            for item in value.splitlines():
                if not item:
                    continue

                if '|' in item:
                    item, display_name = item.split('|')

                    if not item:
                        continue

                    items.append({
                        'value': self.el_type(item),
                        'display_name': display_name,
                    })
                else:
                    items.append({
                        'value': self.el_type(item),
                        'display_name': item,
                    })
            return items
        except Exception as exc:
            raise ValidationError('error comma-separated-%s value "%s"' % (self.el_type.__name__, value))

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_prep_value(self, value):
        if value is None:
            return None

        if not value:
            return ''

        if isinstance(value, (set, )):
            value = list(value)

        if not isinstance(value, list):
            raise ValidationError('value %s is not list, but %s' % (value, type(value).__name__))

        items = []
        for v in value:
            if not isinstance(v, dict):
                raise ValidationError('value item is not dict')

            try:
                self.el_type(v['value'])
            except Exception as _:
                raise ValidationError('value item %s not %s-like' % (v, self.el_type.__name__))

            if v['value'] != v['display_name']:
                items.append('{}|{}'.format(v['value'], v['display_name']))
            else:
                items.append(str(v['value']))

        return '\n'.join(items)

    def formfield(self, **kwargs):
        return super().formfield(**{
            'max_length': self.max_length,
            'el_type': self.el_type,
            'form_class': AttributeChoiceFormField,
            **kwargs,
        })

from functools import lru_cache
import logging
import re
from typing import Tuple, Dict

import jinja2

from unidecode import unidecode

from django.utils.crypto import hashlib
from django.core.cache import cache

from kernel.jinja2.filters import get_filters

from ops.choices import AttributeType, AttributeCatalog

logger = logging.getLogger(__name__)


def get_jinja2_env():
    JINJA2_ENV = jinja2.Environment(undefined=jinja2.ChainableUndefined)
    JINJA2_ENV.filters.update(get_filters())
    return JINJA2_ENV


# Регулярки для нормализации DetailType.designation
_NORMALIZE_RE = re.compile(r'[^a-zA-Z0-9]+')
_MULTIPLE_US_RE = re.compile(r'_+')
_NUMERIC_START_RE = re.compile(r'^\d')

TEMPLATE_KEY = "marktpl:%s"


@lru_cache(maxsize=1024)
def _get_template(src):
    patched_src, alias = preprocess_template(src)
    tpl = get_jinja2_env().from_string(patched_src)

    return tpl


def normalize_designation(designation: str) -> str:
    """
    Преобразует произвольное обозначение (DetailType.designation) в безопасный alias,
    пригодный для использования как переменная в Jinja2-шаблоне.

    - Приводит к нижнему регистру.
    - Транслитерирует через unidecode.
    - Удаляет все символы, кроме латиницы, цифр и подчёркиваний.
    - Убирает повторяющиеся подчёркивания и ведущие/замыкающие подчёркивания.
    - Если начинается с цифры - добавляет подчёркивание в начало.
    - Добавляет префикс 'normalized_' для избежания коллизций.

    Пример:
        "ZOM (тип 1)" -> "normalized_zom_tip_1"

    :param designation: Исходное обозначение типа детали (DetailType.designation)
    :return: Строка в виде 'normalized_<alias>'.
    """
    name = unidecode(designation.strip().lower())
    name = _NORMALIZE_RE.sub('_', name)
    name = _MULTIPLE_US_RE.sub('_', name).strip('_')

    if _NUMERIC_START_RE.match(name):
        name = '_' + name

    return f'normalized_{name}'


# Регулярки для поиска jinja-блоков и угловых скобок
JINJA_EXPR_RE = re.compile(r'({[{%].*?[}%]})', re.S)
DESIG_RE = re.compile(r'<([^<>]+?)>')


def preprocess_template(src: str) -> Tuple[str, Dict[str, str]]:
    """
    Обрабатывает шаблон, заменяя <DetailType.designation> внутри Jinj2-блоков
    ({{ .. }} и {% ... %}) на безопасные alias'ы.

    Например:
        Вход: "{{ <ZOM (тип 1)>.e + 5 }}"
        Выход: "{{ normalized_zom_tip_1.e + 5 }}", {"normalized_zom_tip_1": "ZOM (тип 1)"}

    :param src: Исходная строка-шаблон.
    :return: Кортеж из:
        - обработанного шаблона с заменами,
        - словаря соответствий alias -> оригинальное обозначение.
    """
    mapping = {}

    def _patch_block(block: str) -> str:
        def _sub(m):
            raw = m.group(1)
            alias = normalize_designation(raw)
            mapping[alias] = raw
            return alias
        return DESIG_RE.sub(_sub, block)

    parts = JINJA_EXPR_RE.split(src)
    patched = ''.join(_patch_block(p) if JINJA_EXPR_RE.match(p) else p for p in parts)
    return patched, mapping


class MarkingCompiler:
    """
    Компилятор для постановки данных с Item для формирования маркировки marking объекта Item.
    Создать объект этого класса и вызвать compile. Используется jinja2.

    Если `auto_wrap=True`, автоматически добавляет `{{` и `}}` в начале и конце `marking_template`.
    """

    def __init__(self, item, marking_template=None, auto_wrap=False, extra_context=None, children=None):
        self.item = item
        self.marking_template = marking_template or self.item.variant.marking_template or ""
        self.extra_context = extra_context or {}
        self.children = children

        if auto_wrap and not self.marking_template.startswith('{{') and not self.marking_template.endswith('}}'):
            self.marking_template = f'{{{{ {self.marking_template} }}}}'

    def get_children_context(self, context, children):
        from ops.cache import get_cached_catalog_entry, get_cached_directory_entry
        from ops.models import Attribute, ItemChild
        from catalog.models import DirectoryEntry

        for child in children:
            if isinstance(child, ItemChild):
                index = child.position
                count = getattr(child, 'count', 1)
                child = child.child
            else:
                index = 1
                count = 1

            prefix = normalize_designation(f'{child.type.category}_{child.type.designation}')
            logger.info('prefix: %s', prefix)

            context[prefix] = {}
            context[prefix]['inner_id'] = child.inner_id

            # TODO: deprecated, убрать потом
            # context[prefix]['weight'] = child.weight * count

            if child.parameters:
                attributes = child.variant.get_attributes_dict(cached=True)

                params_context = {}
                for key, value in child.parameters.items():
                    if key not in attributes:
                        continue
                    attribute = attributes[key]

                    if attribute.type == AttributeType.CATALOG and value is not None:
                        allowed_builtin_catalogues = [item for item in AttributeCatalog]

                        if attribute.catalog not in allowed_builtin_catalogues:
                            directory_id = int(value)
                            entry = get_cached_directory_entry(directory_id, value)
                            params_context[key] = entry
                        else:
                            package = f'catalog.models.{attribute.catalog}'
                            instance = get_cached_catalog_entry(package, value)
                            params_context[key] = instance
                    else:
                        params_context[key] = value

                for k, v in list(params_context.items()):
                    if isinstance(v, (int, float)):
                        params_context[k] = v * count

                context[prefix].update(params_context)

            logger.info('context: %s', context)
            context[f'{prefix}.{index}'] = context[prefix]

    def compile(self):
        from ops.cache import get_cached_catalog_entry, get_cached_directory_entry
        from ops.models import Attribute, ItemChild

        # Основные значения
        context = {
            'inner_id': self.item.inner_id,
            'weight': self.item.weight,
        }

        # Включаем в шаблон возможность указать дополнительные параметры с JSON-поля
        # TODO: Кэширование (в redis)
        # TODO: Безопасность jinja2
        if self.item.parameters:
            attributes = self.item.variant.get_attributes_dict(cached=True)

            params_context = {}
            for key, value in self.item.parameters.items():
                if key not in attributes:
                    continue

                attribute = attributes[key]

                if attribute.type == AttributeType.CATALOG and value is not None:
                    allowed_builtin_catalogues = [item for item in AttributeCatalog]

                    if attribute.catalog not in allowed_builtin_catalogues:
                        from catalog.models import DirectoryEntry

                        directory_id = int(value)
                        entry = get_cached_directory_entry(directory_id, value)
                        params_context[key] = entry
                    else:
                        package = f'catalog.models.{attribute.catalog}'
                        instance = get_cached_catalog_entry(package, value)
                        params_context[key] = instance
                else:
                    params_context[key] = value

            context.update(**params_context)

        if self.children:
            self.get_children_context(context, self.children)
        elif self.item.id:
            children = self.item.get_children()
            self.get_children_context(context, children)

        template = _get_template(self.marking_template)

        context.update(**self.extra_context)

        rendered_template = template.render(**context)

        return rendered_template

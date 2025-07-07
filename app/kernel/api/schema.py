from django_filters.rest_framework import FilterSet
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.openapi import Parameter, TYPE_STRING

from rest_framework.permissions import OperandHolder


class AutoSchema(SwaggerAutoSchema):
    """
    Основная схема для Swagger
    """

    def split_summary_from_description(self, description):
        summary = None
        summary_max_len = 120

        sections = description.split('\n', 1)

        if len(sections) == 2:
            sections[0] = sections[0].strip()

            if len(sections[0]) < summary_max_len:
                summary, description = sections
                description = description.strip()

        return summary, description

    def get_query_parameters(self):
        result = super().get_query_parameters()

        if getattr(self.view, 'action', None) in ['list', 'retrieve']:
            result.append(Parameter(
                name='expand', in_='query', description='Расширение поля',
                required=False, type='string',
            ))

        # filterset_class = getattr(self.view, 'filterset_class', None)
        # if filterset_class and issubclass(filterset_class, FilterSet):
        #     for filter_name, filter_instance in filterset_class.declared_filters.items():
        #         result.append(Parameter(
        #             name=filter_name,
        #             in_='query',
        #             description=f"Фильтрация по полю {filter_instance.field_name} с лукапом {filter_instance.lookup_expr}",
        #             required=False,
        #             type=TYPE_STRING,
        #         ))

        return result

    def get_permission_doc(self, permission):
        permission_docs = ""

        if type(permission) == OperandHolder:
            op1_class = permission.op1_class

            if type(op1_class) == OperandHolder:
                permission_docs += self.get_permission_doc(op1_class)
            elif op1_class.__doc__:
                permission_docs += "\t" + op1_class.__doc__.strip() + "\n\n"

            op2_class = permission.op2_class

            if type(op2_class) == OperandHolder:
                permission_docs += self.get_permission_doc(op2_class)
            elif op2_class.__doc__:
                permission_docs += "\t" + op2_class.__doc__.strip() + "\n\n"
        elif permission.__doc__:
            permission_docs += "\t" + permission.__doc__.strip() + "\n\n"

        return permission_docs

    def get_summary_and_description(self):
        summary, description = super().get_summary_and_description()

        permissions = self.view.permission_classes
        permission_description = ''

        for permission in permissions:
            permission_description += self.get_permission_doc(permission)

        if permissions:
            description += '\n\n**Разрешения:**\n\n'
            description += permission_description

        return summary, description

    def get_tags(self, operation_keys=None):
        operation_keys = operation_keys or self.operation_keys

        tags = self.overrides.get('tags')

        if not tags:
            tags = ['/api/' + operation_keys[0]]

        return tags


class MultiPartAutoSchema(AutoSchema):
    """
    Схема предназначенный для views у которых есть возможность загрузить файлы

    В Swagger будет представлен в виде input позволяющий загружать файлы через api
    """

    def get_consumes(self):
        return ['multipart/form-data']

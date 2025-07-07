from rest_framework.filters import OrderingFilter


class FilterSetBuilder:
    def __new__(cls, *args):
        filterset_fields = []

        for field in args:
            if isinstance(field, (tuple, list)):
                field_name = field[0]
                lookups = field[1]

                for lookup in lookups:
                    if lookup == 'exact':
                        filterset_fields.append(field_name)
                    filterset_fields.append(f'{field_name}__{lookup}')
            else:
                filterset_fields.append(field)

        return filterset_fields


class MappedOrderingFilter(OrderingFilter):
    def set_desc(self, field, is_desc):
        if is_desc:
            return f'-{field}'
        else:
            return field

    def get_mapped_fields(self, view, fields):
        mapped_fields = getattr(view, 'ordering_mapped_fields', None)

        if not mapped_fields:
            return fields

        new_fields = []

        for field in fields:
            is_desc = True if field.startswith('-') else False

            if is_desc:
                field = field[1:]

            if field in mapped_fields:
                new_field = mapped_fields[field]
            else:
                new_field = field

            if isinstance(new_field, list):
                new_field = [self.set_desc(field, is_desc) for field in new_field]
                new_fields.extend(new_field)
            else:
                new_field = self.set_desc(new_field, is_desc)
                new_fields.append(new_field)

        return new_fields

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]
            fields = self.get_mapped_fields(view, fields)
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering

        return self.get_default_ordering(view)

from collections import OrderedDict

from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DynamicPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'size'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = None

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)

        if page_size != -1:
            return super().paginate_queryset(queryset, request, view)

        page_number = request.query_params.get(self.page_query_param, 1)

        if page_number != 1:
            raise NotFound

        self.request = request

        return list(queryset)

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ('count', self.page.paginator.count if hasattr(self, 'page') else len(data)),
                    ('size', len(data)),
                    ('next', self.get_next_link() if hasattr(self, 'page') else None),
                    ('previous', self.get_previous_link() if hasattr(self, 'page') else None),
                    ('results', data),
                ]
            )
        )

    def get_paginated_response_schema(self, schema):
        schema = super().get_paginated_response_schema(schema)
        schema['properties']['size'] = {
            'type': 'integer',
            'example': 123,
        }

        return schema

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                size = request.query_params[self.page_size_query_param]

                if size == '-1':
                    return -1
            except (KeyError, ValueError):
                pass

        return super().get_page_size(request)

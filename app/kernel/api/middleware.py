from urllib.parse import parse_qs


class ConvertFiltersToQueryParamsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        filters = request.GET.get('filters')
        if filters:
            parsed_params = parse_qs(filters)

            request.GET._mutable = True
            for key, values in parsed_params.items():
                for value in values:
                    request.GET.appendlist(key, value)

        return self.get_response(request)

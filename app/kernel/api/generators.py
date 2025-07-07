from drf_yasg.generators import OpenAPISchemaGenerator


class SchemaGenerator(OpenAPISchemaGenerator):
    """
    Основной генератор схем для Swagger

    Здесь в основном меняет тип id с integer на string, чтобы можно было использовать 'me' для обозначения,
    текущего пользователя
    """

    def get_path_parameters(self, path, view_cls):
        parameters = super().get_path_parameters(path, view_cls)

        for parameter in parameters:
            if parameter['name'] == 'id':
                parameter['type'] = 'string'

        return parameters

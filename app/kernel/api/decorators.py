from rest_framework.decorators import action


def choices_action(**kwargs):
    """
    Декоратор для маркировки action как choices action.
    """

    kwargs.setdefault('methods', ['get'])
    kwargs.setdefault('detail', False)

    def decorator(func):
        if 'url_path' not in kwargs:
            kwargs['url_path'] = func.__name__

        kwargs['url_path'] = 'choices/' + kwargs['url_path']

        func.is_choices_action = True  # Устанавливаем признак, что это choices action
        return action(**kwargs)(func)

    return decorator

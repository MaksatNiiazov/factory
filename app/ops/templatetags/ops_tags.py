from django import template

register = template.Library()


# увеличит значение на 5 для координат положения на svg
@register.filter(name="add_5")
def add_5(value, arg):
    return int(arg) + 5 * (value - 1)


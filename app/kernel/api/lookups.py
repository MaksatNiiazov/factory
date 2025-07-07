# Фильтрация для строкового поля
STRING_LOOKUPS = ['exact', 'isnull', 'regex', 'in', 'istartswith', 'iendswith', 'icontains']

# Фильтрация для поля даты DateField
DATE_LOOKUPS = ['exact', 'in', 'range', 'lt', 'lte', 'gt', 'gte', 'day', 'week_day', 'month', 'year']

# Фильтрация для поля BooleanField
BOOLEAN_LOOKUPS = ['exact']

# Если CharField содержит choices
CHOICES_LOOKUPS = ['exact', 'in']

# Фильтрация для поля ForeignKey
FOREIGN_KEY_LOOKUPS = ['exact', 'in']

# Фильтрация для поля FloatField
FLOAT_LOOKUPS = ['exact']

# Фильтрация для поля IntegerField
INTEGER_LOOKUPS = ['exact', 'in', 'regex', 'istartswith', 'iendswith', 'icontains']

ARRAY_LOOKUPS = ['in']

from kernel.api import lookups
from kernel.api.filters import create_filterset
from taskmanager.models import Task

TaskFilter = create_filterset(Task, {
    'id': lookups.INTEGER_LOOKUPS,
    'owner': lookups.FOREIGN_KEY_LOOKUPS,
    'type': lookups.CHOICES_LOOKUPS,
    'dry_run': lookups.BOOLEAN_LOOKUPS,
    'status': lookups.CHOICES_LOOKUPS,
})

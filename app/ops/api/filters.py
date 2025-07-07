from kernel.api import lookups
from kernel.api.filters import create_filterset

from ops.models import Project, Item, DetailType, Variant, BaseComposition, Attribute

ProjectFilter = create_filterset(Project, {
    'organization': lookups.FOREIGN_KEY_LOOKUPS,
    'owner': lookups.FOREIGN_KEY_LOOKUPS,
    'number': lookups.STRING_LOOKUPS,
    'status': lookups.CHOICES_LOOKUPS,
    'load_unit': lookups.CHOICES_LOOKUPS,
    'move_unit': lookups.CHOICES_LOOKUPS,
    'temperature_unit': lookups.CHOICES_LOOKUPS,
    'created': lookups.DATE_LOOKUPS,
    'modified': lookups.DATE_LOOKUPS,
    'standard': lookups.CHOICES_LOOKUPS,

})

DetailTypeFilter = create_filterset(DetailType, {
    'product_family': lookups.FOREIGN_KEY_LOOKUPS,
    'name': lookups.STRING_LOOKUPS,
    'designation': lookups.STRING_LOOKUPS,
    'category': lookups.CHOICES_LOOKUPS,
    'branch_qty': lookups.CHOICES_LOOKUPS,
})

ItemFilter = create_filterset(Item, {
    'type': lookups.FOREIGN_KEY_LOOKUPS,
    'variant': lookups.FOREIGN_KEY_LOOKUPS,
    'author': lookups.FOREIGN_KEY_LOOKUPS,
    'material': lookups.FOREIGN_KEY_LOOKUPS,
    'inner_id': lookups.INTEGER_LOOKUPS,
    'name': lookups.STRING_LOOKUPS,
    'marking': lookups.STRING_LOOKUPS,
    'weight': lookups.FLOAT_LOOKUPS,
    'height': lookups.FLOAT_LOOKUPS,
    'erp_id': lookups.STRING_LOOKUPS,
    'created': lookups.DATE_LOOKUPS,
    'modified': lookups.DATE_LOOKUPS,
})

VariantFilter = create_filterset(Variant, {
    'detail_type': lookups.FOREIGN_KEY_LOOKUPS,
    'detail_type__category': lookups.CHOICES_LOOKUPS,
    'name': lookups.STRING_LOOKUPS,
})

BaseCompositionFilter = create_filterset(BaseComposition, {
    'id': lookups.INTEGER_LOOKUPS,
    'base_parent': lookups.FOREIGN_KEY_LOOKUPS,
    'base_parent_variant': lookups.FOREIGN_KEY_LOOKUPS,
    'base_child': lookups.FOREIGN_KEY_LOOKUPS,
    'base_child_variant': lookups.FOREIGN_KEY_LOOKUPS,
})


AttributeFilter = create_filterset(Attribute, {
    'id': lookups.INTEGER_LOOKUPS,
    'detail_type': lookups.FOREIGN_KEY_LOOKUPS,
    'variant': lookups.FOREIGN_KEY_LOOKUPS,
    'name': lookups.STRING_LOOKUPS,
})

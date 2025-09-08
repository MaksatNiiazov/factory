from ops.services.product_selection import ProductSelectionAvailableOptions
from ops.services.shock_selection import ShockSelectionAvailableOptions
from ops.services.spacer_selection import SpacerSelectionAvailableOptions

SELECTION_AVAILABLE_OPTIONS = {
    "product_selection": ProductSelectionAvailableOptions,
    "ssg_selection": SpacerSelectionAvailableOptions,
    "shock_selection": ShockSelectionAvailableOptions,
}

def get_selection_available_options_class(selection_type: str):
    """
    Получает доступные опции для указанного типа подбора.
    """
    available_options_class = SELECTION_AVAILABLE_OPTIONS.get(selection_type)

    if not available_options_class:
        raise ValueError(f"Не найдено доступных опций для типа подбора: {selection_type}")

    return available_options_class

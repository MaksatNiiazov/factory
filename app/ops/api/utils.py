from typing import Tuple
from ..choices import AttributeUsageChoices
from ..models import Attribute
from constance import config


def get_extended_range(L2_avg: float, sn: float, stroke: float) -> Tuple[float, float]:
    """
    Вычисляет расширенный диапазон «холодное/горячее» положение с учётом ±10 % от stroke.

    Args:
        L2_avg: float — среднее положение длины блока (мм)
        sn: float — перемещение поршня (мм)
        stroke: float — номинальный ход (мм)

    Returns:
        (extended_min, extended_max): кортеж из двух float
    """
    abs_sn = abs(sn)
    L_cold = L2_avg - abs_sn
    L_hot = L2_avg + abs_sn
    delta = stroke * config.SSB_EXTRA_MARGIN_PERCENT
    return (L_cold - delta, L_hot + delta)



def sum_mounting_sizes(item, variant_ids):
    total = 0.0
    for vid in variant_ids:
        attr = Attribute.objects.for_variant(vid).filter(name=AttributeUsageChoices.INSTALLATION_SIZE).first()
        if attr:
            raw = item.parameters.get(attr.name)
            try:
                total += float(raw)
                continue
            except Exception:
                pass
            try:
                total += float(attr.default or 0)
            except Exception:
                pass
    return total

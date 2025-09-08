from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from catalog.models import PipeMountingRule, ProductFamily
from ops.api.constants import LOAD_FACTORS, FN_ON_REQUEST
from ops.api.utils import get_extended_range
from ops.choices import AttributeUsageChoices
from ops.models import Item, Variant, Attribute
from constance import config


def calculate_shock_block(data: dict, user):
    from catalog.models import ProductFamily

    item = get_object_or_404(Item, id=data['item_id'])
    catalog = item.parameters.get(config.SSB_CATALOG_PARAM_KEY, [])
    if not isinstance(catalog, list) or not catalog:
        raise ValidationError("Каталог SSB пуст")

    load_type = data['load_type']
    load_value = data['load_value']
    sn = data['sn']
    branch_qty = data['branch_qty']
    pipe_direction = data['pipe_direction']
    mounting_length = data.get('mounting_length_full')
    mounting_vars = data.get('mounting_variants') or []
    use_extra = data['use_extra_margin']

    factor = LOAD_FACTORS[load_type]
    nom_per = (load_value / factor) / branch_qty
    sn_margin = abs(sn) * config.SSB_SN_MARGIN_COEF

    fn_candidates = [
        e for e in catalog
        if isinstance(e.get('fn'), (int, float))
        and e['fn'] != FN_ON_REQUEST
        and e['fn'] >= nom_per
    ]
    if not fn_candidates:
        raise ValidationError("Нагрузка слишком велика")

    family = item.type.product_family
    allow_rod_adjustment = family.has_rod if isinstance(family, ProductFamily) else False

    for fn_entry in sorted(fn_candidates, key=lambda x: x['fn']):
        fn_val = fn_entry['fn']
        stroke_entries = sorted(
            [e for e in catalog if e.get('fn') == fn_val and isinstance(e.get('stroke'), (int, float)) and e['stroke'] >= sn_margin],
            key=lambda x: x['stroke']
        )
        for sel in stroke_entries:
            stroke = sel['stroke']
            L2_min, L2_max, L2_avg = sel['L2_min'], sel['L2_max'], sel['L2_avg']
            L3, L4, block_len = sel['L3'], sel['L4'], sel['block_length']

            if mounting_length is None:
                return {
                    "item_id": item.id,
                    "result": f"SSB {fn_val:04d}.{stroke:03d}.0000.1",
                    "fn": fn_val, "stroke": stroke, "type": 1,
                    "mounting_length": None, "extender": 0.0,
                    "L2_req": round(L2_avg, 3),
                    "L2_min": L2_min, "L2_max": L2_max, "L2_avg": L2_avg,
                    "L3": L3, "L4": L4, "block_length": block_len,
                    "debug": ["#Регулировка не используется: монтажная длина не указана"]
                }

            rule = PipeMountingRule.objects.filter(
                family=family,
                num_spring_blocks=branch_qty,
                pipe_direction=pipe_direction
            ).first()
            if not rule:
                continue

            variant_ids = rule.pipe_mounting_groups.values_list('variants__id', flat=True)
            allowed = Variant.objects.filter(id__in=variant_ids).distinct()
            chosen = allowed.filter(id__in=mounting_vars)
            if chosen.count() != len(mounting_vars):
                continue

            # Суммарная длина креплений
            total_mount = 0.0
            for v in chosen:
                # ⚠️ важно: теперь используем get_available_attributes, чтобы учитывать и базовые атрибуты
                attr = v.get_available_attributes().filter(name=AttributeUsageChoices.INSTALLATION_SIZE).first()
                mount_val = None
                if attr:
                    raw = item.parameters.get(attr.name)
                    if raw is not None:
                        try:
                            mount_val = float(raw)
                        except Exception:
                            pass
                    if mount_val is None and attr.default is not None:
                        try:
                            mount_val = float(attr.default)
                        except Exception:
                            pass
                total_mount += mount_val or 0.0

            L2_req = mounting_length - total_mount
            debug_msg.append(f"#Расчет: mounting_length={mounting_length}, total_mount={total_mount}, L2_req={L2_req}")

            if L2_req < 0:
                continue

            type_ = None
            extender = 0.0
            debug_msg = []
            warning_msg = None

            if allow_rod_adjustment:
                if L2_min <= L2_req <= L2_max:
                    type_ = 1
                    debug_msg.append("#Подбор: Используется регулировка штока")
                    warning_msg = "ВНИМАНИЕ! ПОДБОР НЕСТАНДАРТНЫЙ, РЕГУЛИРОВКА ДЛИНЫ ОСУЩЕСТВЛЯЕТСЯ ЗА СЧЕТ ХОДА ШТОКА!"
                elif use_extra:
                    mn, mx = get_extended_range(L2_avg, sn, stroke)
                    if mn <= L2_req <= mx:
                        type_ = 1
                        debug_msg.append("#Подбор: Регулировка штока с допуском")
                        warning_msg = "ВНИМАНИЕ! ПОДБОР НЕСТАНДАРТНЫЙ, РЕГУЛИРОВКА ДЛИНЫ ОСУЩЕСТВЛЯЕТСЯ ЗА СЧЕТ ХОДА ШТОКА!"

            if not type_:
                type_ = 2
                extender = max(L2_req - block_len, 0.0)
                debug_msg.append("#Подбор: Используется удлинитель (тип 2)")

            return {
                "item_id": item.id,
                "result": f"SSB {fn_val:04d}.{stroke:03d}.{int(mounting_length):04d}.{type_}",
                "fn": fn_val, "stroke": stroke, "type": type_,
                "mounting_length": mounting_length,
                "extender": round(extender, 3),
                "L2_req": round(L2_req, 3),
                "L2_min": L2_min, "L2_max": L2_max, "L2_avg": L2_avg,
                "L3": L3, "L4": L4, "block_length": block_len,
                "debug": debug_msg,
                "warning": warning_msg if allow_rod_adjustment else None
            }

    raise ValidationError("Не удалось подобрать гидроамортизатор для заданных параметров.")


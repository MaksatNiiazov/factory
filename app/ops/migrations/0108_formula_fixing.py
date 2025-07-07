import re
from django.db import migrations
from django.db.models import Q

JINJA_BLOCK_RE = re.compile(r"({[{%].*?[}%]})", re.S)


def compile_designation_regex(designation: str) -> re.Pattern:
    return re.compile(rf"(?<![<_A-Za-z0-9]){re.escape(designation)}(?![A-Za-z0-9])")


def add_category_prefix_jinja(text: str, fix_pairs) -> str:
    def patch_block(block: str) -> str:
        patched = block
        for designation, token in fix_pairs:
            patched = compile_designation_regex(designation).sub(token, patched)
        return patched

    parts = JINJA_BLOCK_RE.split(text)
    return "".join(
        patch_block(p) if JINJA_BLOCK_RE.match(p) else p
        for p in parts
    )


def add_category_prefix_formula(text: str, fix_pairs) -> str:
    if ("{{" in text) or ("{%" in text):
        return add_category_prefix_jinja(text, fix_pairs)

    patched = text
    for designation, token in fix_pairs:
        patched = compile_designation_regex(designation).sub(token, patched)
    return patched


def forwards(apps, schema_editor):
    Variant = apps.get_model("ops", "Variant")
    BaseComposition = apps.get_model("ops", "BaseComposition")
    Attribute = apps.get_model("ops", "Attribute")

    for variant in Variant.objects.filter(deleted_at__isnull=True):
        comps = (
            BaseComposition.objects.filter(
                base_parent_variant=variant, deleted_at__isnull=True,
            ).select_related("base_child")
        )

        fix_pairs = [
            (c.base_child.designation, f"{c.base_child.category}_{c.base_child.designation}")
            for c in comps
        ]
        fix_pairs.sort(key=lambda p: len(p[0]), reverse=True)

        tpl = variant.marking_template or ""
        new_tpl = add_category_prefix_jinja(tpl, fix_pairs)
        if new_tpl != tpl:
            variant.marking_template = new_tpl
            variant.save(update_fields=["marking_template"])

        attrs = Attribute.objects.filter(
            Q(detail_type=variant.detail_type) | Q(variant=variant),
            calculated_value__isnull=False, deleted_at__isnull=True,
        ).exclude(calculated_value="")

        for attr in attrs:
            raw = attr.calculated_value
            patched = add_category_prefix_formula(raw, fix_pairs)
            if patched != raw:
                attr.calculated_value = patched
                attr.save(update_fields=["calculated_value"])


class Migration(migrations.Migration):
    dependencies = [
        ("ops", "0107_variant_series"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=lambda apps, scheme_editor: None),
    ]

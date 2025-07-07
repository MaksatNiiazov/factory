import re

from django.db import migrations
from django.db.models import Q


def normalize_tokens(base_compositions):
    tokens = [
        f"{c.base_child.category}_{c.base_child.designation}"
        for c in base_compositions.select_related("base_child")
    ]
    return sorted(tokens, key=len, reverse=True)


def compile_regex(token):
    return re.compile(rf"(?<!<){re.escape(token)}(?!>)")


def patch_inside_jinja(text, tokens):
    if not tokens:
        return text

    jinja_re = re.compile(r"({[{%].*?[}%]})", re.S)

    def wrap_tokens(block: str):
        patched = block
        for tok in tokens:
            patched = compile_regex(tok).sub(f"<{tok}>", patched)
        return patched

    parts = jinja_re.split(text)

    return "".join(wrap_tokens(p) if jinja_re.match(p) else p for p in parts)


def patch_formula(text, tokens):
    if ("{{" in text) or ("{%" in text):
        return patch_inside_jinja(text, tokens)

    patched = text

    for token in tokens:
        patched = compile_regex(token).sub(f"<{token}>", patched)

    return patched


def forwards(apps, schema_editor):
    Variant = apps.get_model("ops", "Variant")
    BaseComposition = apps.get_model("ops", "BaseComposition")
    Attribute = apps.get_model("ops", "Attribute")

    for variant in Variant.objects.filter(deleted_at__isnull=True):
        base_compositions = BaseComposition.objects.filter(base_parent_variant=variant, deleted_at__isnull=True)
        tokens = normalize_tokens(base_compositions)

        # Сначало по marking_template
        template = variant.marking_template or ""
        new_template = patch_inside_jinja(template, tokens)
        if new_template != template:
            variant.marking_template = new_template
            variant.save(update_fields=["marking_template"])

        # После с атрибутами у которых есть формула
        attrs = Attribute.objects.filter(
            Q(detail_type=variant.detail_type) | Q(variant=variant), deleted_at__isnull=True
        ).exclude(calculated_value__isnull=True).exclude(calculated_value="")

        for attr in attrs:
            raw = attr.calculated_value
            patched = patch_formula(raw, tokens)

            if patched != raw:
                attr.calculated_value = patched
                attr.save(update_fields=["calculated_value"])


class Migration(migrations.Migration):
    dependencies = [
        ("ops", "0108_formula_fixing"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=lambda apps, scheme_editor: None),
    ]

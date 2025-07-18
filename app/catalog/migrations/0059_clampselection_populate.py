from django.db import migrations


DATA = [
    # Зеленые (unlimited)
    {"hanger_load_group": 12, "clamp_load_group": 12, "result": "unlimited"},
    {"hanger_load_group": 16, "clamp_load_group": 12, "result": "unlimited"},
    {"hanger_load_group": 16, "clamp_load_group": 16, "result": "unlimited"},
    {"hanger_load_group": 20, "clamp_load_group": 12, "result": "unlimited"},
    {"hanger_load_group": 20, "clamp_load_group": 16, "result": "unlimited"},
    {"hanger_load_group": 20, "clamp_load_group": 20, "result": "unlimited"},
    {"hanger_load_group": 24, "clamp_load_group": 16, "result": "unlimited"},
    {"hanger_load_group": 24, "clamp_load_group": 20, "result": "unlimited"},
    {"hanger_load_group": 24, "clamp_load_group": 24, "result": "unlimited"},
    {"hanger_load_group": 30, "clamp_load_group": 20, "result": "unlimited"},
    {"hanger_load_group": 30, "clamp_load_group": 24, "result": "unlimited"},
    {"hanger_load_group": 30, "clamp_load_group": 30, "result": "unlimited"},
    {"hanger_load_group": 36, "clamp_load_group": 24, "result": "unlimited"},
    {"hanger_load_group": 36, "clamp_load_group": 30, "result": "unlimited"},
    {"hanger_load_group": 36, "clamp_load_group": 36, "result": "unlimited"},
    {"hanger_load_group": 42, "clamp_load_group": 24, "result": "unlimited"},
    {"hanger_load_group": 42, "clamp_load_group": 30, "result": "unlimited"},
    {"hanger_load_group": 42, "clamp_load_group": 36, "result": "unlimited"},
    {"hanger_load_group": 42, "clamp_load_group": 42, "result": "unlimited"},
    {"hanger_load_group": 48, "clamp_load_group": 30, "result": "unlimited"},
    {"hanger_load_group": 48, "clamp_load_group": 36, "result": "unlimited"},
    {"hanger_load_group": 48, "clamp_load_group": 42, "result": "unlimited"},
    {"hanger_load_group": 48, "clamp_load_group": 48, "result": "unlimited"},
    {"hanger_load_group": 56, "clamp_load_group": 42, "result": "unlimited"},
    {"hanger_load_group": 56, "clamp_load_group": 48, "result": "unlimited"},
    {"hanger_load_group": 56, "clamp_load_group": 56, "result": "unlimited"},
    {"hanger_load_group": 64, "clamp_load_group": 48, "result": "unlimited"},
    {"hanger_load_group": 64, "clamp_load_group": 56, "result": "unlimited"},
    {"hanger_load_group": 64, "clamp_load_group": 64, "result": "unlimited"},
    {"hanger_load_group": 72, "clamp_load_group": 56, "result": "unlimited"},
    {"hanger_load_group": 72, "clamp_load_group": 64, "result": "unlimited"},
    {"hanger_load_group": 72, "clamp_load_group": 72, "result": "unlimited"},
    {"hanger_load_group": 80, "clamp_load_group": 64, "result": "unlimited"},
    {"hanger_load_group": 80, "clamp_load_group": 72, "result": "unlimited"},
    {"hanger_load_group": 80, "clamp_load_group": 80, "result": "unlimited"},
    {"hanger_load_group": 90, "clamp_load_group": 72, "result": "unlimited"},
    {"hanger_load_group": 90, "clamp_load_group": 80, "result": "unlimited"},
    {"hanger_load_group": 90, "clamp_load_group": 90, "result": "unlimited"},

    # Желтые (adapter_required)
    {"hanger_load_group": 12, "clamp_load_group": 16, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 20, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 24, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 30, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 36, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 42, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 48, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 56, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 64, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 72, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 80, "additional_clamp_load_group": 12, "result": "adapter_required"},
    {"hanger_load_group": 12, "clamp_load_group": 90, "additional_clamp_load_group": 12, "result": "adapter_required"},

    {"hanger_load_group": 16, "clamp_load_group": 20, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 24, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 30, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 36, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 42, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 48, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 56, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 64, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 72, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 80, "additional_clamp_load_group": 16, "result": "adapter_required"},
    {"hanger_load_group": 16, "clamp_load_group": 90, "additional_clamp_load_group": 16, "result": "adapter_required"},

    {"hanger_load_group": 20, "clamp_load_group": 24, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 30, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 36, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 42, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 48, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 56, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 64, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 72, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 80, "additional_clamp_load_group": 20, "result": "adapter_required"},
    {"hanger_load_group": 20, "clamp_load_group": 90, "additional_clamp_load_group": 20, "result": "adapter_required"},

    {"hanger_load_group": 24, "clamp_load_group": 30, "additional_clamp_load_group": 24, "result": "adapter_required"},
    {"hanger_load_group": 24, "clamp_load_group": 36, "additional_clamp_load_group": 24, "result": "adapter_required"},
    {"hanger_load_group": 24, "clamp_load_group": 42, "additional_clamp_load_group": 24, "result": "adapter_required"},
    {"hanger_load_group": 24, "clamp_load_group": 48, "additional_clamp_load_group": 24, "result": "adapter_required"},
    {"hanger_load_group": 24, "clamp_load_group": 56, "additional_clamp_load_group": 24, "result": "adapter_required"},
    {"hanger_load_group": 24, "clamp_load_group": 64, "additional_clamp_load_group": 24, "result": "adapter_required"},
    {"hanger_load_group": 24, "clamp_load_group": 72, "additional_clamp_load_group": 24, "result": "adapter_required"},
    {"hanger_load_group": 24, "clamp_load_group": 80, "additional_clamp_load_group": 24, "result": "adapter_required"},
    {"hanger_load_group": 24, "clamp_load_group": 90, "additional_clamp_load_group": 24, "result": "adapter_required"},

    {"hanger_load_group": 30, "clamp_load_group": 36, "additional_clamp_load_group": 30, "result": "adapter_required"},
    {"hanger_load_group": 30, "clamp_load_group": 42, "additional_clamp_load_group": 30, "result": "adapter_required"},
    {"hanger_load_group": 30, "clamp_load_group": 48, "additional_clamp_load_group": 30, "result": "adapter_required"},
    {"hanger_load_group": 30, "clamp_load_group": 56, "additional_clamp_load_group": 30, "result": "adapter_required"},
    {"hanger_load_group": 30, "clamp_load_group": 64, "additional_clamp_load_group": 30, "result": "adapter_required"},
    {"hanger_load_group": 30, "clamp_load_group": 72, "additional_clamp_load_group": 30, "result": "adapter_required"},
    {"hanger_load_group": 30, "clamp_load_group": 80, "additional_clamp_load_group": 30, "result": "adapter_required"},
    {"hanger_load_group": 30, "clamp_load_group": 90, "additional_clamp_load_group": 30, "result": "adapter_required"},

    {"hanger_load_group": 36, "clamp_load_group": 42, "additional_clamp_load_group": 36, "result": "adapter_required"},
    {"hanger_load_group": 36, "clamp_load_group": 48, "additional_clamp_load_group": 36, "result": "adapter_required"},
    {"hanger_load_group": 36, "clamp_load_group": 56, "additional_clamp_load_group": 36, "result": "adapter_required"},
    {"hanger_load_group": 36, "clamp_load_group": 64, "additional_clamp_load_group": 36, "result": "adapter_required"},
    {"hanger_load_group": 36, "clamp_load_group": 72, "additional_clamp_load_group": 36, "result": "adapter_required"},
    {"hanger_load_group": 36, "clamp_load_group": 80, "additional_clamp_load_group": 36, "result": "adapter_required"},
    {"hanger_load_group": 36, "clamp_load_group": 90, "additional_clamp_load_group": 36, "result": "adapter_required"},

    {"hanger_load_group": 42, "clamp_load_group": 48, "additional_clamp_load_group": 42, "result": "adapter_required"},
    {"hanger_load_group": 42, "clamp_load_group": 56, "additional_clamp_load_group": 42, "result": "adapter_required"},
    {"hanger_load_group": 42, "clamp_load_group": 64, "additional_clamp_load_group": 42, "result": "adapter_required"},
    {"hanger_load_group": 42, "clamp_load_group": 72, "additional_clamp_load_group": 42, "result": "adapter_required"},
    {"hanger_load_group": 42, "clamp_load_group": 80, "additional_clamp_load_group": 42, "result": "adapter_required"},
    {"hanger_load_group": 42, "clamp_load_group": 90, "additional_clamp_load_group": 42, "result": "adapter_required"},

    {"hanger_load_group": 48, "clamp_load_group": 56, "additional_clamp_load_group": 48, "result": "adapter_required"},
    {"hanger_load_group": 48, "clamp_load_group": 64, "additional_clamp_load_group": 48, "result": "adapter_required"},
    {"hanger_load_group": 48, "clamp_load_group": 72, "additional_clamp_load_group": 48, "result": "adapter_required"},
    {"hanger_load_group": 48, "clamp_load_group": 80, "additional_clamp_load_group": 48, "result": "adapter_required"},
    {"hanger_load_group": 48, "clamp_load_group": 90, "additional_clamp_load_group": 48, "result": "adapter_required"},

    {"hanger_load_group": 56, "clamp_load_group": 64, "additional_clamp_load_group": 56, "result": "adapter_required"},
    {"hanger_load_group": 56, "clamp_load_group": 72, "additional_clamp_load_group": 56, "result": "adapter_required"},
    {"hanger_load_group": 56, "clamp_load_group": 80, "additional_clamp_load_group": 56, "result": "adapter_required"},
    {"hanger_load_group": 56, "clamp_load_group": 90, "additional_clamp_load_group": 56, "result": "adapter_required"},

    {"hanger_load_group": 64, "clamp_load_group": 72, "additional_clamp_load_group": 64, "result": "adapter_required"},
    {"hanger_load_group": 64, "clamp_load_group": 80, "additional_clamp_load_group": 64, "result": "adapter_required"},
    {"hanger_load_group": 64, "clamp_load_group": 90, "additional_clamp_load_group": 64, "result": "adapter_required"},

    {"hanger_load_group": 72, "clamp_load_group": 80, "additional_clamp_load_group": 72, "result": "adapter_required"},
    {"hanger_load_group": 72, "clamp_load_group": 90, "additional_clamp_load_group": 72, "result": "adapter_required"},

    {"hanger_load_group": 80, "clamp_load_group": 90, "additional_clamp_load_group": 80, "result": "adapter_required"},
    
    # Красные (not_possible)
    {"hanger_load_group": 24, "clamp_load_group": 12, "result": "not_possible"},

    {"hanger_load_group": 30, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 30, "clamp_load_group": 16, "result": "not_possible"},

    {"hanger_load_group": 36, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 36, "clamp_load_group": 16, "result": "not_possible"},
    {"hanger_load_group": 36, "clamp_load_group": 20, "result": "not_possible"},

    {"hanger_load_group": 42, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 42, "clamp_load_group": 16, "result": "not_possible"},
    {"hanger_load_group": 42, "clamp_load_group": 20, "result": "not_possible"},

    {"hanger_load_group": 48, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 48, "clamp_load_group": 16, "result": "not_possible"},
    {"hanger_load_group": 48, "clamp_load_group": 20, "result": "not_possible"},
    {"hanger_load_group": 48, "clamp_load_group": 24, "result": "not_possible"},

    {"hanger_load_group": 56, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 56, "clamp_load_group": 16, "result": "not_possible"},
    {"hanger_load_group": 56, "clamp_load_group": 20, "result": "not_possible"},
    {"hanger_load_group": 56, "clamp_load_group": 24, "result": "not_possible"},
    {"hanger_load_group": 56, "clamp_load_group": 30, "result": "not_possible"},
    {"hanger_load_group": 56, "clamp_load_group": 36, "result": "not_possible"},

    {"hanger_load_group": 64, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 64, "clamp_load_group": 16, "result": "not_possible"},
    {"hanger_load_group": 64, "clamp_load_group": 20, "result": "not_possible"},
    {"hanger_load_group": 64, "clamp_load_group": 24, "result": "not_possible"},
    {"hanger_load_group": 64, "clamp_load_group": 30, "result": "not_possible"},
    {"hanger_load_group": 64, "clamp_load_group": 36, "result": "not_possible"},
    {"hanger_load_group": 64, "clamp_load_group": 42, "result": "not_possible"},

    {"hanger_load_group": 72, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 72, "clamp_load_group": 16, "result": "not_possible"},
    {"hanger_load_group": 72, "clamp_load_group": 20, "result": "not_possible"},
    {"hanger_load_group": 72, "clamp_load_group": 24, "result": "not_possible"},
    {"hanger_load_group": 72, "clamp_load_group": 30, "result": "not_possible"},
    {"hanger_load_group": 72, "clamp_load_group": 36, "result": "not_possible"},
    {"hanger_load_group": 72, "clamp_load_group": 42, "result": "not_possible"},
    {"hanger_load_group": 72, "clamp_load_group": 48, "result": "not_possible"},

    {"hanger_load_group": 80, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 80, "clamp_load_group": 16, "result": "not_possible"},
    {"hanger_load_group": 80, "clamp_load_group": 20, "result": "not_possible"},
    {"hanger_load_group": 80, "clamp_load_group": 24, "result": "not_possible"},
    {"hanger_load_group": 80, "clamp_load_group": 30, "result": "not_possible"},
    {"hanger_load_group": 80, "clamp_load_group": 36, "result": "not_possible"},
    {"hanger_load_group": 80, "clamp_load_group": 42, "result": "not_possible"},
    {"hanger_load_group": 80, "clamp_load_group": 48, "result": "not_possible"},
    {"hanger_load_group": 80, "clamp_load_group": 56, "result": "not_possible"},

    {"hanger_load_group": 90, "clamp_load_group": 12, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 16, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 20, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 24, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 30, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 36, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 42, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 48, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 56, "result": "not_possible"},
    {"hanger_load_group": 90, "clamp_load_group": 64, "result": "not_possible"},
]


def populate_clampselection_matrix(apps, schema_editor):
    ClampSelectionMatrix = apps.get_model("catalog", "ClampSelectionMatrix")
    ClampSelectionEntry = apps.get_model("catalog", "ClampSelectionEntry")

    matrix = ClampSelectionMatrix.objects.create()

    objects = []

    for entry in DATA:
        objects.append(
            ClampSelectionEntry(
                matrix=matrix,
                hanger_load_group=entry["hanger_load_group"],
                clamp_load_group=entry["clamp_load_group"],
                additional_clamp_load_group=entry.get("additional_clamp_load_group"),
                result=entry["result"]
            )
        )
    
    ClampSelectionEntry.objects.bulk_create(objects)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0058_alter_clampselectionmatrix_product_family"),
    ]

    operations = [
        migrations.RunPython(populate_clampselection_matrix),
    ]

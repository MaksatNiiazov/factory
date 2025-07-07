from django.db import migrations, models


def populate_clampmaterialcoefficient(apps, schema_editor):
    ClampMaterialCoefficient = apps.get_model("catalog", "ClampMaterialCoefficient")

    coefficients = [
        # 09Г2С, группа 16
        {"material_group": "16", "temperature": 100, "coefficient": 1.0},
        {"material_group": "16", "temperature": 150, "coefficient": 1.0},
        {"material_group": "16", "temperature": 200, "coefficient": 0.95},
        {"material_group": "16", "temperature": 250, "coefficient": 0.87},
        {"material_group": "16", "temperature": 300, "coefficient": 0.76},
        {"material_group": "16", "temperature": 350, "coefficient": 0.72},
        {"material_group": "16", "temperature": 400, "coefficient": 0.68},
        {"material_group": "16", "temperature": 450, "coefficient": 0.65},
        # 15ХМ, группа 13
        {"material_group": "13", "temperature": 100, "coefficient": 1.0},
        {"material_group": "13", "temperature": 150, "coefficient": 1.0},
        {"material_group": "13", "temperature": 200, "coefficient": 1.0},
        {"material_group": "13", "temperature": 250, "coefficient": 0.97},
        {"material_group": "13", "temperature": 300, "coefficient": 0.9},
        {"material_group": "13", "temperature": 350, "coefficient": 0.85},
        {"material_group": "13", "temperature": 400, "coefficient": 0.8},
        {"material_group": "13", "temperature": 450, "coefficient": 0.76},
        {"material_group": "13", "temperature": 480, "coefficient": 0.75},
        {"material_group": "13", "temperature": 500, "coefficient": 0.58},
        {"material_group": "13", "temperature": 520, "coefficient": 0.4},
        {"material_group": "13", "temperature": 540, "coefficient": 0.25},
        {"material_group": "13", "temperature": 560, "coefficient": 0.17},
        # 1.4541, группа 41
        {"material_group": "41", "temperature": 100, "coefficient": 0.88},
        {"material_group": "41", "temperature": 150, "coefficient": 0.82},
        {"material_group": "41", "temperature": 200, "coefficient": 0.78},
        {"material_group": "41", "temperature": 250, "coefficient": 0.75},
        {"material_group": "41", "temperature": 300, "coefficient": 0.71},
        {"material_group": "41", "temperature": 350, "coefficient": 0.69},
        {"material_group": "41", "temperature": 400, "coefficient": 0.66},
        {"material_group": "41", "temperature": 450, "coefficient": 0.65},
        {"material_group": "41", "temperature": 480, "coefficient": 0.64},
        {"material_group": "41", "temperature": 500, "coefficient": 0.63},
        {"material_group": "41", "temperature": 520, "coefficient": 0.62},
        {"material_group": "41", "temperature": 540, "coefficient": 0.62},
        {"material_group": "41", "temperature": 560, "coefficient": 0.62},
        {"material_group": "41", "temperature": 580, "coefficient": 0.61},
        {"material_group": "41", "temperature": 600, "coefficient": 0.6},
        # 1.4571, группа 71
        {"material_group": "71", "temperature": 100, "coefficient": 0.92},
        {"material_group": "71", "temperature": 150, "coefficient": 0.87},
        {"material_group": "71", "temperature": 200, "coefficient": 0.83},
        {"material_group": "71", "temperature": 250, "coefficient": 0.79},
        {"material_group": "71", "temperature": 300, "coefficient": 0.74},
        {"material_group": "71", "temperature": 350, "coefficient": 0.72},
        {"material_group": "71", "temperature": 400, "coefficient": 0.69},
        {"material_group": "71", "temperature": 450, "coefficient": 0.68},
        {"material_group": "71", "temperature": 480, "coefficient": 0.68},
        {"material_group": "71", "temperature": 500, "coefficient": 0.67},
        {"material_group": "71", "temperature": 520, "coefficient": 0.66},
        {"material_group": "71", "temperature": 540, "coefficient": 0.66},
        {"material_group": "71", "temperature": 560, "coefficient": 0.66},
        {"material_group": "71", "temperature": 580, "coefficient": 0.64},
        {"material_group": "71", "temperature": 600, "coefficient": 0.63},
    ]
    
    for coeff in coefficients:
        ClampMaterialCoefficient.objects.create(**coeff)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0047_clampmaterialcoefficient"),
    ]

    operations = [
        migrations.RunPython(populate_clampmaterialcoefficient),
    ]

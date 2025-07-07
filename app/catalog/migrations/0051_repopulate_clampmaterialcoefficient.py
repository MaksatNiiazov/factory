from django.db import migrations, models


def repopulate_clampmaterialcoefficient(apps, schema_editor):
    ClampMaterialCoefficient = apps.get_model("catalog", "ClampMaterialCoefficient")

    ClampMaterialCoefficient.objects.all().delete()

    coefficients = [
        # 09Г2С, группа 16
        {"material_group": "16", "temperature_from": None, "temperature_to": 99, "coefficient": 1.0},
        {"material_group": "16", "temperature_from": 100, "temperature_to": 149, "coefficient": 1.0},
        {"material_group": "16", "temperature_from": 150, "temperature_to": 199, "coefficient": 1.0},
        {"material_group": "16", "temperature_from": 200, "temperature_to": 249, "coefficient": 0.95},
        {"material_group": "16", "temperature_from": 250, "temperature_to": 299, "coefficient": 0.87},
        {"material_group": "16", "temperature_from": 300, "temperature_to": 349, "coefficient": 0.76},
        {"material_group": "16", "temperature_from": 350, "temperature_to": 399, "coefficient": 0.72},
        {"material_group": "16", "temperature_from": 400, "temperature_to": 449, "coefficient": 0.68},
        {"material_group": "16", "temperature_from": 450, "temperature_to": 479, "coefficient": 0.65},
        # 15ХМ, группа 13
        {"material_group": "13", "temperature_from": None, "temperature_to": 99, "coefficient": 1.0},
        {"material_group": "13", "temperature_from": 100, "temperature_to": 149, "coefficient": 1.0},
        {"material_group": "13", "temperature_from": 150, "temperature_to": 199, "coefficient": 1.0},
        {"material_group": "13", "temperature_from": 200, "temperature_to": 249, "coefficient": 1.0},
        {"material_group": "13", "temperature_from": 250, "temperature_to": 299, "coefficient": 0.97},
        {"material_group": "13", "temperature_from": 300, "temperature_to": 349, "coefficient": 0.9},
        {"material_group": "13", "temperature_from": 350, "temperature_to": 399, "coefficient": 0.85},
        {"material_group": "13", "temperature_from": 400, "temperature_to": 449, "coefficient": 0.8},
        {"material_group": "13", "temperature_from": 450, "temperature_to": 479, "coefficient": 0.76},
        {"material_group": "13", "temperature_from": 480, "temperature_to": 499, "coefficient": 0.75},
        {"material_group": "13", "temperature_from": 500, "temperature_to": 519, "coefficient": 0.58},
        {"material_group": "13", "temperature_from": 520, "temperature_to": 539, "coefficient": 0.4},
        {"material_group": "13", "temperature_from": 540, "temperature_to": 559, "coefficient": 0.25},
        {"material_group": "13", "temperature_from": 560, "temperature_to": 479, "coefficient": 0.17},
        # 1.4541, группа 41
        {"material_group": "41", "temperature_from": None, "temperature_to": 99, "coefficient": 0.88},
        {"material_group": "41", "temperature_from": 100, "temperature_to": 149, "coefficient": 0.88},
        {"material_group": "41", "temperature_from": 150, "temperature_to": 199, "coefficient": 0.82},
        {"material_group": "41", "temperature_from": 200, "temperature_to": 249, "coefficient": 0.78},
        {"material_group": "41", "temperature_from": 250, "temperature_to": 299, "coefficient": 0.75},
        {"material_group": "41", "temperature_from": 300, "temperature_to": 349, "coefficient": 0.71},
        {"material_group": "41", "temperature_from": 350, "temperature_to": 399, "coefficient": 0.69},
        {"material_group": "41", "temperature_from": 400, "temperature_to": 449, "coefficient": 0.66},
        {"material_group": "41", "temperature_from": 450, "temperature_to": 479, "coefficient": 0.65},
        {"material_group": "41", "temperature_from": 480, "temperature_to": 499, "coefficient": 0.64},
        {"material_group": "41", "temperature_from": 500, "temperature_to": 519, "coefficient": 0.63},
        {"material_group": "41", "temperature_from": 520, "temperature_to": 539, "coefficient": 0.62},
        {"material_group": "41", "temperature_from": 540, "temperature_to": 559, "coefficient": 0.62},
        {"material_group": "41", "temperature_from": 560, "temperature_to": 579, "coefficient": 0.62},
        {"material_group": "41", "temperature_from": 580, "temperature_to": 599, "coefficient": 0.61},
        {"material_group": "41", "temperature_from": 600, "temperature_to": None, "coefficient": 0.6},
        # 1.4571, группа 71
        {"material_group": "71", "temperature_from": None, "temperature_to": 99, "coefficient": 0.92},
        {"material_group": "71", "temperature_from": 100, "temperature_to": 149, "coefficient": 0.92},
        {"material_group": "71", "temperature_from": 150, "temperature_to": 199, "coefficient": 0.87},
        {"material_group": "71", "temperature_from": 200, "temperature_to": 249, "coefficient": 0.83},
        {"material_group": "71", "temperature_from": 250, "temperature_to": 299, "coefficient": 0.79},
        {"material_group": "71", "temperature_from": 300, "temperature_to": 349, "coefficient": 0.74},
        {"material_group": "71", "temperature_from": 350, "temperature_to": 399, "coefficient": 0.72},
        {"material_group": "71", "temperature_from": 400, "temperature_to": 449, "coefficient": 0.69},
        {"material_group": "71", "temperature_from": 450, "temperature_to": 479, "coefficient": 0.68},
        {"material_group": "71", "temperature_from": 480, "temperature_to": 499, "coefficient": 0.68},
        {"material_group": "71", "temperature_from": 500, "temperature_to": 519, "coefficient": 0.67},
        {"material_group": "71", "temperature_from": 520, "temperature_to": 539, "coefficient": 0.66},
        {"material_group": "71", "temperature_from": 540, "temperature_to": 559, "coefficient": 0.66},
        {"material_group": "71", "temperature_from": 560, "temperature_to": 579, "coefficient": 0.66},
        {"material_group": "71", "temperature_from": 580, "temperature_to": 599, "coefficient": 0.64},
        {"material_group": "71", "temperature_from": 600, "temperature_to": None, "coefficient": 0.63},
    ]
    
    for coeff in coefficients:
        ClampMaterialCoefficient.objects.create(**coeff)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0050_alter_clampmaterialcoefficient_options_and_more"),
    ]

    operations = [
        migrations.RunPython(repopulate_clampmaterialcoefficient),
    ]

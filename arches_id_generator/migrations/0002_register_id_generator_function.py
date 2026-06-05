from django.db import migrations

from arches_id_generator.constants import FUNCTION_ID


def forward(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.update_or_create(
        functionid=FUNCTION_ID,
        defaults={
            "name": "ID Generator",
            "functiontype": "lifecyclehandler",
            "description": (
                "Generates IDs for nodes configured with the id-generator widget, "
                "either at tile save or on resource lifecycle activation."
            ),
            "defaultconfig": {},
            "modulename": "id_generator_function.py",
            "classname": "IdGeneratorFunction",
            "component": "",
        },
    )


def reverse(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.filter(functionid=FUNCTION_ID).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arches_id_generator", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]

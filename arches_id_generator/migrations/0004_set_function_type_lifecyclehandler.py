from django.db import migrations

from arches_id_generator.constants import FUNCTION_ID


def forward(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.filter(functionid=FUNCTION_ID).update(
        functiontype="lifecyclehandler",
    )


def reverse(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.filter(functionid=FUNCTION_ID).update(functiontype="node")


class Migration(migrations.Migration):

    dependencies = [
        ("arches_id_generator", "0003_register_number_widget"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]

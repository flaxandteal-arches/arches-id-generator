import json
import pathlib

from django.db import migrations

from arches_id_generator.constants import NUMBER_WIDGET_ID

_WIDGET_JSON = (
    pathlib.Path(__file__).resolve().parent.parent
    / "widgets"
    / "number-id-generator-widget.json"
)


def forward(apps, schema_editor):
    Widget = apps.get_model("models", "Widget")
    spec = json.loads(_WIDGET_JSON.read_text())
    Widget.objects.update_or_create(
        widgetid=spec["widgetid"],
        defaults={
            "name": spec["name"],
            "component": spec["component"],
            "datatype": spec["datatype"],
            "defaultconfig": spec["defaultconfig"],
            "helptext": spec.get("helptext"),
        },
    )


def reverse(apps, schema_editor):
    Widget = apps.get_model("models", "Widget")
    Widget.objects.filter(widgetid=NUMBER_WIDGET_ID).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arches_id_generator", "0002_register_id_generator_function"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]

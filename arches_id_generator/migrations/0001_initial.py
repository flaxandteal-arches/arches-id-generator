from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IdSequence",
            fields=[
                (
                    "key",
                    models.CharField(max_length=255, primary_key=True, serialize=False),
                ),
                ("start_number", models.BigIntegerField(default=1)),
                ("next_number", models.BigIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "id_generator_sequence",
            },
        ),
    ]

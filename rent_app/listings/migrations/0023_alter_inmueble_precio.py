# Generated by Django 5.1.3 on 2024-12-17 21:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0022_alter_inmueble_descripcion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inmueble",
            name="precio",
            field=models.CharField(max_length=10),
        ),
    ]

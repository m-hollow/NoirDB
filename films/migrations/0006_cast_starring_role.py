# Generated by Django 3.0.8 on 2020-08-25 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films', '0005_auto_20200804_0228'),
    ]

    operations = [
        migrations.AddField(
            model_name='cast',
            name='starring_role',
            field=models.BooleanField(default=False),
        ),
    ]

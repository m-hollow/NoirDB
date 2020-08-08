# Generated by Django 3.0.8 on 2020-08-04 01:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films', '0003_dailymovie'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailymovie',
            name='current_selection',
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name='dailymovie',
            constraint=models.UniqueConstraint(condition=models.Q(current_selection=True), fields=('current_selection',), name='one current record only'),
        ),
    ]

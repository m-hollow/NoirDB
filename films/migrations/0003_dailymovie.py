# Generated by Django 3.0.8 on 2020-08-04 01:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('films', '0002_movie_display_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyMovie',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_posted', models.DateTimeField(auto_now_add=True)),
                ('daily_count', models.PositiveIntegerField(default=0)),
                ('current_selection', models.BooleanField(default=True)),
                ('movie', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='films.Movie')),
            ],
        ),
    ]

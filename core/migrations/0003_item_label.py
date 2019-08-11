# Generated by Django 2.2 on 2019-08-11 10:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_item_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='label',
            field=models.CharField(choices=[('NA', 'NewA'), ('BS', 'BestSeller')], default='', max_length=2),
        ),
    ]

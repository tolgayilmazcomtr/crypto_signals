# Generated by Django 5.1.4 on 2025-01-01 12:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customuser',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        migrations.AddField(
            model_name='customuser',
            name='package',
            field=models.CharField(choices=[('free', 'Ücretsiz'), ('pro', 'Pro')], default='free', max_length=10),
        ),
        migrations.AlterField(
            model_name='cryptopair',
            name='market_cap',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
    ]
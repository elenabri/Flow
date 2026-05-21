from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_savedcontractor_foreign_reg_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='eridintegration',
            name='external_id',
            field=models.CharField(default='', max_length=255, unique=False, verbose_name='Внешний ID креатива в ОРД'),
            preserve_default=False,
        ),
      
    ]

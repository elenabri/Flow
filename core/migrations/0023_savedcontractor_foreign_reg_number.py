from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_remove_user_telegram_handle_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedcontractor',
            name='foreign_reg_number',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Рег. номер иностранного лица'),
        ),
    ]

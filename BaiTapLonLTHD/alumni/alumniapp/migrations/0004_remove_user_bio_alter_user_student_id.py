# Generated by Django 5.1.5 on 2025-02-03 16:41

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alumniapp', '0003_alter_comment_content_alter_group_description_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='bio',
        ),
        migrations.AlterField(
            model_name='user',
            name='student_id',
            field=models.CharField(blank=True, max_length=20, null=True, validators=[django.core.validators.RegexValidator(message='Mã số sinh viên phải là 8 chữ số', regex='^\\d{8}$')]),
        ),
    ]

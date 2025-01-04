# Generated by Django 5.1.4 on 2025-01-03 00:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translations", "0005_alter_emailverification_token"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="bank_iban",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="bank_swift_code",
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="bank_account_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("CHECKING", "Checking Account"),
                    ("SAVINGS", "Savings Account"),
                ],
                max_length=20,
            ),
        ),
    ]
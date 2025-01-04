# Generated by Django 5.1.4 on 2025-01-03 04:15

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translations", "0006_remove_userprofile_bank_iban_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="translationrequest",
            name="additional_context",
            field=models.JSONField(
                blank=True, help_text="Métadonnées spécifiques au contexte", null=True
            ),
        ),
        migrations.AddField(
            model_name="translationrequest",
            name="duration_minutes",
            field=models.PositiveIntegerField(
                blank=True, help_text="Durée estimée en minutes", null=True
            ),
        ),
        migrations.AddField(
            model_name="translationrequest",
            name="meeting_link",
            field=models.URLField(
                blank=True, help_text="Lien pour les réunions distantes", null=True
            ),
        ),
        migrations.AddField(
            model_name="translationrequest",
            name="phone_number",
            field=models.CharField(
                blank=True,
                help_text="Numéro pour les appels téléphoniques",
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="translationrequest",
            name="client",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="client_requests",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="translationrequest",
            name="client_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AlterField(
            model_name="translationrequest",
            name="original_document",
            field=models.FileField(
                blank=True, null=True, upload_to="original_documents/"
            ),
        ),
        migrations.AlterField(
            model_name="translationrequest",
            name="translated_document",
            field=models.FileField(
                blank=True, null=True, upload_to="translated_documents/"
            ),
        ),
        migrations.AlterField(
            model_name="translationrequest",
            name="translator_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]

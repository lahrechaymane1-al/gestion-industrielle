from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards_create_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserAccessProfile = apps.get_model("app", "UserAccessProfile")
    for user in User.objects.all():
        role = "ADMIN" if getattr(user, "is_superuser", False) else "RU"
        UserAccessProfile.objects.get_or_create(user_id=user.pk, defaults={"role": role})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("app", "0016_productionberceau_temps_arrets_hourly"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserAccessProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(
                    choices=[("PSP", "PSP"), ("RU", "RU"), ("ADMIN", "ADMIN")],
                    default="RU",
                    max_length=10,
                )),
                (
                    "effectif",
                    models.ForeignKey(
                        blank=True,
                        help_text="Pour PSP : l'operateur Effectif dont le shift fait foi.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="linked_users",
                        to="app.operateureffectif",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Profil d'acces",
                "verbose_name_plural": "Profils d'acces",
            },
        ),
        migrations.RunPython(forwards_create_profiles, noop),
    ]

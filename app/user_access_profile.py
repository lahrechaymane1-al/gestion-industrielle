from django.conf import settings
from django.db import models


class UserAccessProfile(models.Model):
    """RBAC profile linked to Django User; shift for PSP comes from Effectif dynamically."""

    class Role(models.TextChoices):
        PSP = "PSP", "PSP"
        RU = "RU", "RU"
        ADMIN = "ADMIN", "ADMIN"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_profile",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.RU)
    effectif = models.ForeignKey(
        "effectif.OperateurEffectif",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="linked_users",
        help_text="Pour PSP : l'operateur Effectif dont le shift fait foi.",
    )

    class Meta:
        verbose_name = "Profil d'acces"
        verbose_name_plural = "Profils d'acces"
        db_table = "app_useraccessprofile"
        managed = False

    def __str__(self):
        return f"{self.user.username} ({self.role})"


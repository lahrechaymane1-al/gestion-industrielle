from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ModeDegrade(models.Model):
    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))
    STATUS_CHOICES = (("Ouvert", "Ouvert"), ("En cours", "En cours"), ("Clos", "Clos"))
    EQUIPE_CHOICES = (("Berceau", "Berceau"), ("CCB", "CCB"))

    equipe = models.CharField("Equipe", max_length=20, choices=EQUIPE_CHOICES)
    shift = models.CharField("Shift", max_length=1, choices=SHIFT_CHOICES)
    action = models.CharField("Action", max_length=255)
    probleme = models.CharField("Probleme", max_length=255)
    pilote = models.CharField("Pilote", max_length=180)
    date = models.DateField("Date")
    delai = models.DateField("Delai")
    cause = models.CharField("Cause", max_length=255)
    statut = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default="Ouvert")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mode_degrade_updated_berceau_area",
    )
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date", "shift"]
        db_table = "app_modedegrade"
        managed = False

    def clean(self):
        super().clean()
        for field_name in ("action", "probleme", "pilote", "cause"):
            value = getattr(self, field_name, "")
            setattr(self, field_name, " ".join(str(value).strip().split()))

    def __str__(self):
        return f"{self.equipe} - {self.date} - {self.probleme}"


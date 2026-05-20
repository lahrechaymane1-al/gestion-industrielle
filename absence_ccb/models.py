from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from effectif_ccb.models import OperateurEffectif

User = get_user_model()


class Absence(models.Model):
    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))
    MIGRATION_STATUS_CHOICES = (
        ("ok", "OK"),
        ("a_corriger", "A corriger"),
    )

    equipe = models.CharField(
        "Equipe",
        max_length=20,
        choices=(("Berceau", "Berceau"), ("CCB", "CCB")),
    )
    effectif = models.ForeignKey(
        OperateurEffectif,
        verbose_name="Personne absente",
        on_delete=models.PROTECT,
        related_name="absences",
        null=True,
        blank=True,
    )
    remplacant_effectif = models.ForeignKey(
        OperateurEffectif,
        verbose_name="Remplacant (effectif)",
        on_delete=models.PROTECT,
        related_name="remplacements_absence",
        null=True,
        blank=True,
    )
    shift = models.CharField("Shift", max_length=1, choices=SHIFT_CHOICES, default="A")
    motif = models.CharField("Motif", max_length=255)
    remplacant = models.CharField("Remplacant externe", max_length=180, blank=True)
    nom_complet = models.CharField("Nom complet (legacy)", max_length=180, blank=True, default="")
    date_absence = models.DateField("Date absence")
    commentaire = models.TextField("Commentaire", blank=True)
    migration_status = models.CharField(
        "Statut migration",
        max_length=20,
        choices=MIGRATION_STATUS_CHOICES,
        default="ok",
    )
    migration_note = models.CharField("Note migration", max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="absences_updated_ccb_area",
    )
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_absence", "id"]
        db_table = "app_absence"
        managed = False

    def clean(self):
        super().clean()
        self.nom_complet = " ".join((self.nom_complet or "").strip().split())
        self.motif = " ".join((self.motif or "").strip().split())
        self.remplacant = " ".join((self.remplacant or "").strip().split())
        self.commentaire = (self.commentaire or "").strip()

        max_len = getattr(settings, "ABSENCE_MOTIF_MAX_LENGTH", 255)
        if not self.motif:
            raise ValidationError({"motif": "Le motif est obligatoire."})
        if len(self.motif) > max_len:
            raise ValidationError({"motif": f"Le motif ne doit pas depasser {max_len} caracteres."})
        if self.effectif_id:
            self.nom_complet = self.effectif.nom_complet
        if not self.nom_complet:
            raise ValidationError({"nom_complet": "Le nom complet est obligatoire."})
        if self.effectif_id is None and self.migration_status != "a_corriger":
            raise ValidationError({"effectif": "La personne absente est obligatoire."})
        if self.remplacant_effectif_id and self.effectif_id and self.remplacant_effectif_id == self.effectif_id:
            raise ValidationError({"remplacant_effectif": "Le remplacant doit etre different de la personne absente."})
        absent_name = (self.effectif.nom_complet if self.effectif_id else self.nom_complet).strip().lower()
        if self.remplacant and absent_name and self.remplacant.strip().lower() == absent_name:
            raise ValidationError({"remplacant": "Le remplacant doit etre different de la personne absente."})
        if self.remplacant and self.remplacant_effectif_id:
            raise ValidationError({"remplacant": "Choisir un remplacant effectif OU saisir un remplacant externe."})
        if not self.remplacant and not self.remplacant_effectif_id:
            raise ValidationError(
                {
                    "remplacant": "Le remplacant est obligatoire (texte ou employe).",
                    "remplacant_effectif": "Le remplacant est obligatoire (texte ou employe).",
                }
            )

    @property
    def absent_nom(self):
        if self.effectif_id:
            return self.effectif.nom_complet
        return self.nom_complet or "-"

    @property
    def remplacant_nom(self):
        if self.remplacant_effectif_id:
            return self.remplacant_effectif.nom_complet
        return self.remplacant or "-"

    def __str__(self):
        return f"{self.absent_nom} - {self.date_absence} ({self.equipe})"


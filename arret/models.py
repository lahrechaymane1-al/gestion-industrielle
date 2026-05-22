from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ArretCategory(models.TextChoices):
    MAINTENANCE = "maintenance", "Maintenance"
    KTA = "kta", "KTA"
    LOGISTIQUE = "logistique", "Logistique"
    FABRICATION = "fabrication", "Fabrication"


class BerceauModule(models.Model):
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "app_berceaumodule"
        managed = False

    def __str__(self):
        return self.name


class BerceauPoste(models.Model):
    module = models.ForeignKey(BerceauModule, on_delete=models.CASCADE, related_name="postes")
    name = models.CharField(max_length=120)
    a1_enabled = models.BooleanField(default=True)
    a3_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["module__name", "name"]
        db_table = "app_berceauposte"
        managed = False

    def __str__(self):
        return f"{self.module.name} - {self.name}"


class BerceauMoyen(models.Model):
    poste = models.ForeignKey(BerceauPoste, on_delete=models.CASCADE, related_name="moyens")
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["poste__module__name", "poste__name", "name"]
        db_table = "app_berceaumoyen"
        managed = False

    def __str__(self):
        return f"{self.poste} - {self.name}"


class PanneType(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="panne_types_updated_berceau_area",
    )

    class Meta:
        ordering = ["name"]
        db_table = "app_pannetype"
        managed = False

    def __str__(self):
        return self.name


class ArretBerceau(models.Model):
    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))

    module = models.ForeignKey(BerceauModule, on_delete=models.PROTECT, related_name="arrets")
    poste = models.ForeignKey(BerceauPoste, on_delete=models.PROTECT, related_name="arrets")
    moyen = models.ForeignKey(BerceauMoyen, on_delete=models.PROTECT, related_name="arrets")
    date = models.DateField()
    shift = models.CharField(max_length=1, choices=SHIFT_CHOICES)
    heure_production = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    temps_arret_min = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    category = models.CharField(
        max_length=20,
        choices=ArretCategory.choices,
        default=ArretCategory.FABRICATION,
    )
    commentaire = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="arrets_berceau_updated_area",
    )

    class Meta:
        ordering = ["-date", "shift", "heure_production"]
        db_table = "app_arretberceau"
        managed = False

    def clean(self):
        super().clean()
        if self.poste_id and self.module_id and self.poste.module_id != self.module_id:
            raise ValidationError({"poste": "Le poste selectionne n'appartient pas au module."})
        if self.moyen_id and self.poste_id and self.moyen and self.moyen.poste_id != self.poste_id:
            raise ValidationError({"moyen": "Le moyen selectionne n'appartient pas au poste."})


class AlertePanne(models.Model):
    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))

    module = models.ForeignKey(BerceauModule, on_delete=models.PROTECT, related_name="alertes_pannes")
    poste = models.ForeignKey(BerceauPoste, on_delete=models.PROTECT, related_name="alertes_pannes")
    moyen = models.ForeignKey(
        BerceauMoyen,
        on_delete=models.PROTECT,
        related_name="alertes_pannes",
        null=True,
        blank=True,
    )
    panne_type = models.ForeignKey(PanneType, on_delete=models.PROTECT, related_name="alertes_pannes")
    cause = models.TextField()
    solution = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=ArretCategory.choices,
        default=ArretCategory.FABRICATION,
    )
    date = models.DateField()
    shift = models.CharField(max_length=1, choices=SHIFT_CHOICES)
    heure_production = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    temps_arret_min = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    equipe = models.CharField(max_length=20, default="Berceau")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alertes_pannes_updated_area",
    )

    class Meta:
        ordering = ["-date", "shift", "-created_at"]
        db_table = "app_alertepanne"
        managed = False

    def clean(self):
        super().clean()
        if self.poste_id and self.module_id and self.poste.module_id != self.module_id:
            raise ValidationError({"poste": "Le poste selectionne n'appartient pas au module."})
        if self.moyen_id and self.poste_id and self.moyen and self.moyen.poste_id != self.poste_id:
            raise ValidationError({"moyen": "Le moyen selectionne n'appartient pas au poste."})


import re
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class OperateurEffectif(models.Model):
    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))
    SEXE_CHOICES = (("Homme", "Homme"), ("Femme", "Femme"))
    CONTRAT_CHOICES = (("CDI", "CDI"), ("CDD", "CDD"), ("ANAPEC", "ANAPEC"))
    EQUIPE_CHOICES = (("Berceau", "Berceau"), ("CCB", "CCB"))
    FONCTION_CHOICES = (
        ("PSP", "PSP"),
        ("OPERATEUR", "OPERATEUR"),
    )

    nom_complet = models.CharField("Nom complet", max_length=180, default="N/A")
    shift = models.CharField("Shift", max_length=1, choices=SHIFT_CHOICES, default="A")
    cin = models.CharField("CIN", max_length=32, unique=True)
    type_contrat = models.CharField("Type de contrat", max_length=20, choices=CONTRAT_CHOICES, default="CDI")
    date_naissance = models.DateField("Date de naissance", default=date(1990, 1, 1))
    date_entree = models.DateField("Date d'entree", default=date(2010, 1, 1))
    identifiant = models.CharField("Identifiant", max_length=64, unique=True)
    matricule = models.CharField("Matricule", max_length=64, blank=True, default="", db_index=True)
    num_tel = models.CharField("Numero de telephone", max_length=24, default="+212600000000")
    sexe = models.CharField("Sexe", max_length=10, choices=SEXE_CHOICES, default="Homme")
    fonction = models.CharField("Fonction", max_length=20, choices=FONCTION_CHOICES, default="OPERATEUR")
    ville_actuelle = models.CharField("Ville actuelle", max_length=120, default="N/A")
    niveau_etude = models.CharField("Niveau d'etude", max_length=120, default="N/A")
    numero_casier = models.CharField("Numero de casier", max_length=32, default="N/A")
    parada_transport = models.CharField("Parada de transport", max_length=120, default="N/A")
    pointure_chaussure = models.PositiveIntegerField(
        "Pointure de chaussure", validators=[MinValueValidator(1)]
    )
    specialite = models.CharField("Specialite", max_length=120, default="N/A")
    taille_pantalon = models.CharField("Taille pantalon", max_length=20, default="M")
    taille_veste = models.CharField("Taille veste", max_length=20, default="M")
    ville_origine = models.CharField("Ville origine", max_length=120, default="N/A")
    equipe = models.CharField("Equipe", max_length=20, choices=EQUIPE_CHOICES)
    psp_lead = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_members",
        help_text="PSP responsable de cette equipe operateur.",
    )
    code_equipe = models.CharField(
        "Code equipe",
        max_length=24,
        blank=True,
        default="",
        db_index=True,
        help_text="Code court partage par le PSP et ses operateurs (meme equipe) pour synchroniser le shift.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="effectifs_updated_berceau_area",
    )
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["nom_complet"]
        db_table = "app_operateureffectif"
        managed = False

    def __str__(self):
        return f"{self.nom_complet} - {self.equipe}"

    def clean(self):
        super().clean()
        self._normalize_strings()
        self._validate_dates()
        self._validate_phone()
        if self.pk and self.psp_lead_id == self.pk:
            raise ValidationError({"psp_lead": "Un operateur ne peut pas etre son propre PSP responsable."})

    def _normalize_strings(self):
        for field_name in (
            "nom_complet",
            "cin",
            "identifiant",
            "matricule",
            "num_tel",
            "fonction",
            "ville_actuelle",
            "niveau_etude",
            "numero_casier",
            "parada_transport",
            "specialite",
            "taille_pantalon",
            "taille_veste",
            "ville_origine",
            "code_equipe",
        ):
            value = getattr(self, field_name, "")
            setattr(self, field_name, " ".join(str(value).strip().split()))

    def _validate_dates(self):
        today = date.today()
        if self.date_naissance >= today:
            raise ValidationError({"date_naissance": "La date de naissance doit etre dans le passe."})
        minimum_age = getattr(settings, "EFFECTIF_MIN_AGE", 18)
        min_entry_date = self.date_naissance.replace(year=self.date_naissance.year + minimum_age)
        if self.date_entree < min_entry_date:
            raise ValidationError(
                {"date_entree": f"La date d'entree doit respecter un age minimum de {minimum_age} ans."}
            )

    def _validate_phone(self):
        raw = (self.num_tel or "").strip()
        if not raw:
            return
        if not re.match(r"^\+?[0-9]{8,15}$", raw):
            raise ValidationError(
                {"num_tel": "Le numero de telephone doit contenir 8 a 15 chiffres (option + au debut)."}
            )
        
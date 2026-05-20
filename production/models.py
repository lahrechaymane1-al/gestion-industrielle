from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum


class ProductionBerceau(models.Model):
    LINE_CHOICES = (("A1", "A1"), ("A3", "A3"))
    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))

    line = models.CharField(max_length=2, choices=LINE_CHOICES, verbose_name="Diversité")
    date = models.DateField(verbose_name="Date")
    shift = models.CharField(max_length=1, choices=SHIFT_CHOICES, verbose_name="Shift")
    objectif = models.PositiveIntegerField(default=337, verbose_name="Objectif")
    objectif_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Objectif H1")
    objectif_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Objectif H2")
    objectif_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Objectif H3")
    objectif_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Objectif H4")
    objectif_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Objectif H5")
    objectif_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Objectif H6")
    objectif_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Objectif H7")
    objectif_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Objectif H8")
    production_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H1")
    production_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H2")
    production_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H3")
    production_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H4")
    production_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H5")
    production_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H6")
    production_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H7")
    production_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H8")
    line_h1 = models.CharField(max_length=2, choices=LINE_CHOICES, default="A1", verbose_name="Diversité H1")
    line_h2 = models.CharField(max_length=2, choices=LINE_CHOICES, default="A1", verbose_name="Diversité H2")
    line_h3 = models.CharField(max_length=2, choices=LINE_CHOICES, default="A1", verbose_name="Diversité H3")
    line_h4 = models.CharField(max_length=2, choices=LINE_CHOICES, default="A1", verbose_name="Diversité H4")
    line_h5 = models.CharField(max_length=2, choices=LINE_CHOICES, default="A1", verbose_name="Diversité H5")
    line_h6 = models.CharField(max_length=2, choices=LINE_CHOICES, default="A1", verbose_name="Diversité H6")
    line_h7 = models.CharField(max_length=2, choices=LINE_CHOICES, default="A1", verbose_name="Diversité H7")
    line_h8 = models.CharField(max_length=2, choices=LINE_CHOICES, default="A1", verbose_name="Diversité H8")
    rebut_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H1")
    rebut_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H2")
    rebut_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H3")
    rebut_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H4")
    rebut_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H5")
    rebut_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H6")
    rebut_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H7")
    rebut_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H8")
    retouche_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche H1")
    retouche_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche H2")
    retouche_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche H3")
    retouche_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche H4")
    retouche_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche H5")
    retouche_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche H6")
    retouche_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche H7")
    retouche_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche H8")
    temps_arrets_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Temps arrets H1")
    temps_arrets_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Temps arrets H2")
    temps_arrets_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Temps arrets H3")
    temps_arrets_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Temps arrets H4")
    temps_arrets_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Temps arrets H5")
    temps_arrets_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Temps arrets H6")
    temps_arrets_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Temps arrets H7")
    temps_arrets_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Temps arrets H8")
    volume = models.PositiveIntegerField(validators=[MinValueValidator(0)], verbose_name="Volume")
    rebut = models.PositiveIntegerField(validators=[MinValueValidator(0)], verbose_name="Rebut")
    retouche = models.PositiveIntegerField(validators=[MinValueValidator(0)], verbose_name="Retouche")
    temps_arrets = models.PositiveIntegerField(
        validators=[MinValueValidator(0)], verbose_name="Temps d'arrets"
    )
    validated_hours_mask = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-date", "line", "shift"]
        db_table = "app_productionberceau"
        managed = False

    @property
    def ro_percent(self):
        if self.objectif <= 0:
            return 0
        return round((self.volume / self.objectif) * 100, 2)

    @property
    def nro_total(self):
        return max((self.objectif or 0) - (self.volume or 0), 0)

    def is_hour_validated(self, hour: int) -> bool:
        if hour < 1 or hour > 8:
            return False
        return bool(self.validated_hours_mask & (1 << (hour - 1)))

    def validate_hour(self, hour: int) -> None:
        if hour < 1 or hour > 8:
            raise ValueError("Heure invalide.")
        self.validated_hours_mask |= 1 << (hour - 1)

    @property
    def validated_hours(self) -> list[int]:
        return [h for h in range(1, 9) if self.is_hour_validated(h)]

    def save(self, *args, **kwargs):
        self._sync_hourly_arrets_from_sources()
        votes_a1 = sum(
            1 for i in range(1, 9) if getattr(self, f"line_h{i}", None) == "A1"
        )
        votes_a3 = sum(
            1 for i in range(1, 9) if getattr(self, f"line_h{i}", None) == "A3"
        )
        if votes_a3 > votes_a1:
            self.line = "A3"
        else:
            self.line = "A1"
        self.volume = (
            self.production_h1
            + self.production_h2
            + self.production_h3
            + self.production_h4
            + self.production_h5
            + self.production_h6
            + self.production_h7
            + self.production_h8
        )
        # Aligner l'objectif global sur la somme H1–H8 (sinon RO / tendances dashboard restent faux
        # après modification des seuls objectifs horaires).
        hourly_objectif = sum(int(getattr(self, f"objectif_h{h}", 0) or 0) for h in range(1, 9))
        if hourly_objectif > 0:
            self.objectif = hourly_objectif
        self.rebut = (
            self.rebut_h1
            + self.rebut_h2
            + self.rebut_h3
            + self.rebut_h4
            + self.rebut_h5
            + self.rebut_h6
            + self.rebut_h7
            + self.rebut_h8
        )
        self.retouche = (
            self.retouche_h1
            + self.retouche_h2
            + self.retouche_h3
            + self.retouche_h4
            + self.retouche_h5
            + self.retouche_h6
            + self.retouche_h7
            + self.retouche_h8
        )
        self.temps_arrets = (
            self.temps_arrets_h1
            + self.temps_arrets_h2
            + self.temps_arrets_h3
            + self.temps_arrets_h4
            + self.temps_arrets_h5
            + self.temps_arrets_h6
            + self.temps_arrets_h7
            + self.temps_arrets_h8
        )
        super().save(*args, **kwargs)

    def compute_hourly_arrets_from_sources(self) -> dict[int, int]:
        from arret.models import AlertePanne, ArretBerceau

        arret_rows = (
            ArretBerceau.objects.filter(date=self.date, shift=self.shift)
            .values("heure_production")
            .annotate(total=Sum("temps_arret_min"))
        )
        alerte_rows = (
            AlertePanne.objects.filter(
                date=self.date, shift=self.shift, equipe="Berceau", is_deleted=False
            )
            .values("heure_production")
            .annotate(total=Sum("temps_arret_min"))
        )
        by_hour = {hour: 0 for hour in range(1, 9)}
        for r in arret_rows:
            hour = int(r["heure_production"])
            by_hour[hour] = by_hour.get(hour, 0) + int(r["total"] or 0)
        for r in alerte_rows:
            hour = int(r["heure_production"])
            by_hour[hour] = by_hour.get(hour, 0) + int(r["total"] or 0)
        return by_hour

    def _sync_hourly_arrets_from_sources(self):
        by_hour = self.compute_hourly_arrets_from_sources()
        for hour in range(1, 9):
            setattr(self, f"temps_arrets_h{hour}", by_hour.get(hour, 0))


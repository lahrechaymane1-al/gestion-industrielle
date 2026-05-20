from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from app.ccb_constants import CCB_OBJECTIF_TOTAL_SHIFT


class ProductionCCB(models.Model):
    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))

    date = models.DateField(verbose_name="Date")
    shift = models.CharField(max_length=1, choices=SHIFT_CHOICES, verbose_name="Shift")
    objectif = models.PositiveIntegerField(default=CCB_OBJECTIF_TOTAL_SHIFT, verbose_name="Objectif")
    production_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H1")
    production_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H2")
    production_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H3")
    production_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H4")
    production_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H5")
    production_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H6")
    production_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H7")
    production_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H8")
    rebut_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H1")
    rebut_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H2")
    rebut_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H3")
    rebut_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H4")
    rebut_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H5")
    rebut_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H6")
    rebut_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H7")
    rebut_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut H8")
    volume = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Volume")
    rebut = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Rebut")
    retouche = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Retouche")
    temps_arrets = models.PositiveIntegerField(
        validators=[MinValueValidator(0)], verbose_name="Temps d'arrets"
    )

    class Meta:
        ordering = ["-date", "shift"]
        db_table = "app_productionccb"
        managed = False

    @property
    def ro_percent(self):
        if self.objectif <= 0:
            return 0
        return round((self.volume / self.objectif) * 100, 2)

    def compute_temps_arrets_from_alertes(self) -> int:
        """Somme des temps d'arrêt (minutes) des alertes panne CCB pour cette date et shift."""
        from arret.models import AlertePanne

        total = (
            AlertePanne.objects.filter(
                date=self.date,
                shift=self.shift,
                equipe="CCB",
                is_deleted=False,
            ).aggregate(t=Sum("temps_arret_min"))
            .get("t")
        )
        return int(total or 0)

    def temps_arrets_by_hour(self) -> dict[int, int]:
        from arret.models import AlertePanne

        rows = (
            AlertePanne.objects.filter(
                date=self.date,
                shift=self.shift,
                equipe="CCB",
                is_deleted=False,
            )
            .values("heure_production")
            .annotate(total=Sum("temps_arret_min"))
        )
        out = {h: 0 for h in range(1, 9)}
        for r in rows:
            h = int(r["heure_production"])
            if 1 <= h <= 8:
                out[h] = int(r["total"] or 0)
        return out

    def save(self, *args, **kwargs):
        """Objectif total fixe ; volume/rebut = sommes horaires ; arrêts depuis les alertes CCB."""
        self.objectif = CCB_OBJECTIF_TOTAL_SHIFT
        self.volume = sum(getattr(self, f"production_h{i}") for i in range(1, 9))
        self.rebut = sum(getattr(self, f"rebut_h{i}") for i in range(1, 9))
        self.temps_arrets = self.compute_temps_arrets_from_alertes()
        super().save(*args, **kwargs)


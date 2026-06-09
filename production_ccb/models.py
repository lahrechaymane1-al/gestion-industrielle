from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from app.ccb_constants import CCB_OBJECTIF_TOTAL_SHIFT, CCB_OBJECTIFS_HORAIRES


class CcbProductionSettings(models.Model):
    """Objectifs horaires par défaut CCB (singleton, toutes dates / shifts)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    objectif_h1 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H1")
    objectif_h2 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H2")
    objectif_h3 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H3")
    objectif_h4 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H4")
    objectif_h5 = models.PositiveIntegerField(default=11, validators=[MinValueValidator(0)], verbose_name="Objectif H5")
    objectif_h6 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H6")
    objectif_h7 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H7")
    objectif_h8 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H8")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paramètres production CCB"
        verbose_name_plural = "Paramètres production CCB"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def objectifs_tuple(self) -> tuple[int, ...]:
        return tuple(int(getattr(self, f"objectif_h{h}", 0) or 0) for h in range(1, 9))

    def objectif_total(self) -> int:
        total = sum(self.objectifs_tuple())
        return total if total > 0 else CCB_OBJECTIF_TOTAL_SHIFT

    @classmethod
    def get_singleton(cls) -> "CcbProductionSettings":
        defaults = {f"objectif_h{h}": int(CCB_OBJECTIFS_HORAIRES[h - 1]) for h in range(1, 9)}
        obj, _ = cls.objects.get_or_create(pk=1, defaults=defaults)
        return obj


def ccb_default_objectifs_horaires() -> tuple[int, ...]:
    try:
        return CcbProductionSettings.get_singleton().objectifs_tuple()
    except Exception:
        return CCB_OBJECTIFS_HORAIRES


class ProductionCCB(models.Model):
    LINE_CHOICES = (("LHD", "LHD"), ("RHD", "RHD"))
    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))

    date = models.DateField(verbose_name="Date")
    shift = models.CharField(max_length=1, choices=SHIFT_CHOICES, verbose_name="Shift")
    line = models.CharField(
        max_length=3,
        choices=LINE_CHOICES,
        default="LHD",
        blank=True,
        verbose_name="Diversité dominante",
    )
    objectif = models.PositiveIntegerField(default=CCB_OBJECTIF_TOTAL_SHIFT, verbose_name="Objectif")
    objectif_h1 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H1")
    objectif_h2 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H2")
    objectif_h3 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H3")
    objectif_h4 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H4")
    objectif_h5 = models.PositiveIntegerField(default=11, validators=[MinValueValidator(0)], verbose_name="Objectif H5")
    objectif_h6 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H6")
    objectif_h7 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H7")
    objectif_h8 = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)], verbose_name="Objectif H8")
    production_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H1")
    production_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H2")
    production_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H3")
    production_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H4")
    production_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H5")
    production_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H6")
    production_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H7")
    production_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Production H8")
    production_lhd_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. LHD H1")
    production_lhd_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. LHD H2")
    production_lhd_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. LHD H3")
    production_lhd_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. LHD H4")
    production_lhd_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. LHD H5")
    production_lhd_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. LHD H6")
    production_lhd_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. LHD H7")
    production_lhd_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. LHD H8")
    production_rhd_h1 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. RHD H1")
    production_rhd_h2 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. RHD H2")
    production_rhd_h3 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. RHD H3")
    production_rhd_h4 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. RHD H4")
    production_rhd_h5 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. RHD H5")
    production_rhd_h6 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. RHD H6")
    production_rhd_h7 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. RHD H7")
    production_rhd_h8 = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Prod. RHD H8")
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

    def _sync_hourly_production_from_diversities(self) -> None:
        lhd_total = 0
        rhd_total = 0
        for hour in range(1, 9):
            lhd = int(getattr(self, f"production_lhd_h{hour}", 0) or 0)
            rhd = int(getattr(self, f"production_rhd_h{hour}", 0) or 0)
            setattr(self, f"production_h{hour}", lhd + rhd)
            lhd_total += lhd
            rhd_total += rhd
        if rhd_total > lhd_total:
            self.line = "RHD"
        else:
            self.line = "LHD"

    def save(self, *args, **kwargs):
        self._sync_hourly_production_from_diversities()
        self.volume = sum(int(getattr(self, f"production_h{h}", 0) or 0) for h in range(1, 9))
        self.rebut = sum(int(getattr(self, f"rebut_h{h}", 0) or 0) for h in range(1, 9))
        hourly_objectif = sum(int(getattr(self, f"objectif_h{h}", 0) or 0) for h in range(1, 9))
        if hourly_objectif > 0:
            self.objectif = hourly_objectif
        else:
            try:
                self.objectif = CcbProductionSettings.get_singleton().objectif_total()
            except Exception:
                self.objectif = CCB_OBJECTIF_TOTAL_SHIFT
        self.temps_arrets = self.compute_temps_arrets_from_alertes()
        super().save(*args, **kwargs)

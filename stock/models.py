from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class StockJournal(models.Model):
    EQUIPE_CHOICES = (("Berceau", "Berceau"), ("CCB", "CCB"))
    LINE_CHOICES = (("A1", "A1"), ("A3", "A3"))

    date = models.DateField()
    equipe = models.CharField(max_length=20, choices=EQUIPE_CHOICES, default="Berceau")
    line = models.CharField(max_length=2, choices=LINE_CHOICES, null=True, blank=True)
    stock_debut = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    entree_calculee = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    sortie_montage = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    stock_fin = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    is_closed = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_journal_updated",
    )

    class Meta:
        db_table = "stock_journal"
        ordering = ["-date", "equipe", "line"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "equipe", "line"],
                name="uniq_stock_journal_date_equipe_line",
            )
        ]

    def __str__(self) -> str:
        scope = f"{self.equipe}-{self.line}" if self.line else self.equipe
        return f"{scope} {self.date.isoformat()}"


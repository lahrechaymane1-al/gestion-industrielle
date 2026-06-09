from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class ConsommableItem(models.Model):
    """Catalog item that can be purchased by UEP Berceau/CCB."""

    EQUIPE_CHOICES = (("Berceau", "Berceau"), ("CCB", "CCB"))
    TYPE_CHOICES = (
        ("EPIs", "EPIs"),
        ("AUTRE", "AUTRE"),
        ("FOURNITURE", "FOURNITURE"),
        ("PR BERCEAU", "PR BERCEAU"),
        ("PR TORCHE MANUELLE", "PR TORCHE MANUELLE"),
        ("PRODUIT CHIMIQUE", "PRODUIT CHIMIQUE"),
    )

    equipe = models.CharField(max_length=20, choices=EQUIPE_CHOICES, default="Berceau")
    type_materiel = models.CharField(max_length=40, default="AUTRE")
    name = models.CharField(max_length=120)
    reference = models.CharField(max_length=80)
    unit_price_eur = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "consommable_item"
        ordering = ["equipe", "name", "reference"]
        constraints = [
            models.UniqueConstraint(
                fields=["equipe", "reference", "name"],
                name="uniq_consommable_item_equipe_reference_name",
            )
        ]

    def __str__(self) -> str:
        return f"{self.equipe} - {self.name} ({self.reference})"


class ConsommablePurchase(models.Model):
    """A purchase line using one catalog item."""

    SHIFT_CHOICES = (("A", "A"), ("B", "B"), ("N", "N"))

    equipe = models.CharField(max_length=20, choices=ConsommableItem.EQUIPE_CHOICES, default="Berceau")
    shift = models.CharField(max_length=1, choices=SHIFT_CHOICES)
    item = models.ForeignKey(ConsommableItem, on_delete=models.PROTECT, related_name="purchases")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price_eur = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    total_price_eur = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    purchase_date = models.DateField()
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="consommable_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="consommable_updated"
    )

    class Meta:
        db_table = "consommable_purchase"
        ordering = ["-purchase_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.equipe} - {self.item.reference} x{self.quantity}"


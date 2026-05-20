from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    AlertePanne,
    Absence,
    ArretBerceau,
    BerceauModule,
    BerceauMoyen,
    BerceauPoste,
    ModeDegrade,
    OperateurEffectif,
    PanneType,
    ProductionBerceau,
    ProductionCCB,
    UserAccessProfile,
)

User = get_user_model()


@admin.register(OperateurEffectif)
class OperateurEffectifAdmin(admin.ModelAdmin):
    list_display = (
        "nom_complet",
        "identifiant",
        "equipe",
        "shift",
        "fonction",
        "linked_login_summary",
    )
    list_filter = ("equipe", "shift", "fonction", "is_deleted")
    search_fields = ("nom_complet", "identifiant", "cin", "num_tel")
    readonly_fields = ("linked_login_detail",)

    @admin.display(description="Compte Django lie (profil)")
    def linked_login_summary(self, obj: OperateurEffectif) -> str:
        profiles = UserAccessProfile.objects.filter(effectif_id=obj.pk).select_related("user")
        parts = [f"{p.user.username} ({p.role})" for p in profiles]
        return ", ".join(parts) if parts else "—"

    @admin.display(description="Detail profils lies")
    def linked_login_detail(self, obj: OperateurEffectif | None) -> str:
        if obj is None or obj.pk is None:
            return "Enregistrez la fiche pour voir les profils lies."
        profiles = UserAccessProfile.objects.filter(effectif_id=obj.pk).select_related("user")
        if not profiles:
            return (
                "Aucun UserAccessProfile ne pointe vers cette fiche. "
                "Pour lier un PSP : Utilisateurs → choisir le compte → section « Profil d'acces » → champ Effectif."
            )
        return "\n".join(f"{p.user.username}: role={p.role}, profil_id={p.pk}" for p in profiles)


class UserAccessProfileInline(admin.StackedInline):
    """Expose le lien Role + Effectif directement sur la fiche Utilisateur."""

    model = UserAccessProfile
    can_delete = False
    max_num = 1
    fk_name = "user"
    verbose_name = "Profil d'acces (role, effectif PSP)"
    verbose_name_plural = "Profil d'acces"
    autocomplete_fields = ("effectif",)
    fields = ("role", "effectif")


class UserAdmin(DjangoUserAdmin):
    inlines = (*DjangoUserAdmin.inlines, UserAccessProfileInline)


@admin.register(UserAccessProfile)
class UserAccessProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "effectif", "effectif_equipe_shift")
    list_filter = ("role",)
    search_fields = ("user__username", "effectif__identifiant", "effectif__nom_complet")
    autocomplete_fields = ("user", "effectif")

    @admin.display(description="Equipe / shift (effectif)")
    def effectif_equipe_shift(self, obj: UserAccessProfile) -> str:
        eff = obj.effectif
        if eff is None:
            return "—"
        return f"{eff.equipe} · shift {eff.shift}"


if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(ProductionBerceau)
admin.site.register(ProductionCCB)
admin.site.register(Absence)
admin.site.register(ModeDegrade)
admin.site.register(BerceauModule)
admin.site.register(BerceauPoste)
admin.site.register(BerceauMoyen)
admin.site.register(PanneType)
admin.site.register(ArretBerceau)
admin.site.register(AlertePanne)

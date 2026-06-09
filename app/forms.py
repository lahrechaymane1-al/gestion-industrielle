from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from .ccb_constants import CCB_OBJECTIF_TOTAL_SHIFT
from .models import Absence, ModeDegrade, OperateurEffectif, ProductionBerceau, ProductionCCB, UserAccessProfile


class LoginForm(forms.Form):
    identifiant = forms.CharField(label="Identifiant", required=True)
    code = forms.CharField(label="Code", widget=forms.PasswordInput, required=True)


class ProductionBerceauForm(forms.ModelForm):
    class Meta:
        model = ProductionBerceau
        fields = [
            "line",
            "date",
            "shift",
            "objectif",
            "objectif_h1",
            "objectif_h2",
            "objectif_h3",
            "objectif_h4",
            "objectif_h5",
            "objectif_h6",
            "objectif_h7",
            "objectif_h8",
            "line_h1",
            "line_h2",
            "line_h3",
            "line_h4",
            "line_h5",
            "line_h6",
            "line_h7",
            "line_h8",
            "production_h1",
            "production_h2",
            "production_h3",
            "production_h4",
            "production_h5",
            "production_h6",
            "production_h7",
            "production_h8",
            "rebut_h1",
            "rebut_h2",
            "rebut_h3",
            "rebut_h4",
            "rebut_h5",
            "rebut_h6",
            "rebut_h7",
            "rebut_h8",
            "retouche_h1",
            "retouche_h2",
            "retouche_h3",
            "retouche_h4",
            "retouche_h5",
            "retouche_h6",
            "retouche_h7",
            "retouche_h8",
            "temps_arrets_h1",
            "temps_arrets_h2",
            "temps_arrets_h3",
            "temps_arrets_h4",
            "temps_arrets_h5",
            "temps_arrets_h6",
            "temps_arrets_h7",
            "temps_arrets_h8",
            "rebut",
            "retouche",
            "temps_arrets",
        ]
        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "date-picker-input",
                    "data-open-picker": "true",
                    "autocomplete": "off",
                }
            ),
        }
        labels = {
            "line": "Diversité",
            "shift": "Shift",
        }

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        shift = cleaned.get("shift")
        if date and shift:
            query = ProductionBerceau.objects.filter(date=date, shift=shift)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise ValidationError(
                    "Une production existe deja pour cette date et ce shift."
                )
        if cleaned.get("retouche") is None:
            cleaned["retouche"] = 0
        if cleaned.get("temps_arrets") is None:
            cleaned["temps_arrets"] = 0
        hourly_arret_values = [cleaned.get(f"temps_arrets_h{i}") for i in range(1, 9)]
        has_hourly_arret = any(v not in (None, "") for v in hourly_arret_values)
        if has_hourly_arret:
            cleaned["temps_arrets"] = sum(int(v or 0) for v in hourly_arret_values)
        hourly_rebut_values = [cleaned.get(f"rebut_h{i}") for i in range(1, 9)]
        if any(v not in (None, "") for v in hourly_rebut_values):
            cleaned["rebut"] = sum(int(v or 0) for v in hourly_rebut_values)
        hourly_retouche_values = [cleaned.get(f"retouche_h{i}") for i in range(1, 9)]
        if any(v not in (None, "") for v in hourly_retouche_values):
            cleaned["retouche"] = sum(int(v or 0) for v in hourly_retouche_values)
        return cleaned


class OperateurEffectifForm(forms.ModelForm):
    class Meta:
        model = OperateurEffectif
        fields = [
            "nom_complet",
            "equipe",
            "shift",
            "psp_lead",
            "cin",
            "type_contrat",
            "date_naissance",
            "date_entree",
            "identifiant",
            "matricule",
            "num_tel",
            "sexe",
            "fonction",
            "ville_actuelle",
            "niveau_etude",
            "numero_casier",
            "parada_transport",
            "pointure_chaussure",
            "specialite",
            "taille_pantalon",
            "taille_veste",
            "ville_origine",
        ]
        widgets = {
            "date_naissance": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "date-picker-input",
                    "data-open-picker": "true",
                    "autocomplete": "off",
                }
            ),
            "date_entree": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "date-picker-input",
                    "data-open-picker": "true",
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        equipe = getattr(self.instance, "equipe", None) or (getattr(self, "initial", None) or {}).get("equipe")
        psp_ids = UserAccessProfile.objects.filter(
            role=UserAccessProfile.Role.PSP,
            effectif_id__isnull=False,
        ).values_list("effectif_id", flat=True)
        qs = OperateurEffectif.objects.filter(is_deleted=False).filter(
            Q(fonction="PSP") | Q(pk__in=psp_ids)
        )
        if equipe:
            qs = qs.filter(equipe=equipe)
        if self.instance.pk and self.instance.psp_lead_id:
            qs = qs | OperateurEffectif.objects.filter(pk=self.instance.psp_lead_id)
        self.fields["psp_lead"].queryset = qs.distinct().order_by("nom_complet")
        self.fields["psp_lead"].required = False
        self.fields["psp_lead"].empty_label = "Aucun (PSP lead)"
        self.fields["psp_lead"].label = "PSP responsable"
        self.fields["psp_lead"].help_text = (
            "Lien equipe : seuls les operateurs avec ce PSP en « PSP responsable » sont visibles en session PSP."
        )


class ProductionCCBForm(forms.ModelForm):
    class Meta:
        model = ProductionCCB
        fields = [
            "date",
            "shift",
            "objectif",
            "objectif_h1",
            "objectif_h2",
            "objectif_h3",
            "objectif_h4",
            "objectif_h5",
            "objectif_h6",
            "objectif_h7",
            "objectif_h8",
            "production_lhd_h1",
            "production_lhd_h2",
            "production_lhd_h3",
            "production_lhd_h4",
            "production_lhd_h5",
            "production_lhd_h6",
            "production_lhd_h7",
            "production_lhd_h8",
            "production_rhd_h1",
            "production_rhd_h2",
            "production_rhd_h3",
            "production_rhd_h4",
            "production_rhd_h5",
            "production_rhd_h6",
            "production_rhd_h7",
            "production_rhd_h8",
            "rebut_h1",
            "rebut_h2",
            "rebut_h3",
            "rebut_h4",
            "rebut_h5",
            "rebut_h6",
            "rebut_h7",
            "rebut_h8",
            "retouche",
        ]
        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "date-picker-input",
                    "data-open-picker": "true",
                    "autocomplete": "off",
                }
            ),
        }
        labels = {
            "shift": "Shift",
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("retouche") is None:
            cleaned["retouche"] = 0
        date = cleaned.get("date")
        shift = cleaned.get("shift")
        if date and shift:
            query = ProductionCCB.objects.filter(date=date, shift=shift)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise ValidationError(
                    "Une production CCB existe deja pour cette combinaison date/shift."
                )
        return cleaned


class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = [
            "effectif",
            "nom_complet",
            "shift",
            "motif",
            "date_absence",
            "remplacant_effectif",
            "remplacant",
            "commentaire",
        ]
        widgets = {
            "date_absence": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "date-picker-input",
                    "data-open-picker": "true",
                    "autocomplete": "off",
                }
            ),
            "nom_complet": forms.TextInput(attrs={"readonly": "readonly"}),
        }

    def clean(self):
        cleaned = super().clean()
        effectif = cleaned.get("effectif")
        nom_complet = " ".join((cleaned.get("nom_complet") or "").strip().split())
        date_absence = cleaned.get("date_absence")
        equipe = getattr(self.instance, "equipe", None)
        remplacant_effectif = cleaned.get("remplacant_effectif")
        remplacant = (cleaned.get("remplacant") or "").strip()
        motif = " ".join((cleaned.get("motif") or "").strip().split())
        cleaned["motif"] = motif
        if effectif:
            nom_complet = effectif.nom_complet
        cleaned["nom_complet"] = nom_complet
        if not nom_complet:
            self.add_error("nom_complet", "Le nom complet est obligatoire.")
        if not motif:
            self.add_error("motif", "Le motif est obligatoire.")
        if not date_absence:
            self.add_error("date_absence", "La date d'absence est obligatoire.")
        if effectif and date_absence and equipe:
            if effectif.equipe != equipe:
                raise ValidationError("La personne absente ne correspond pas a l'equipe selectionnee.")
            query = Absence.objects.filter(
                effectif=effectif,
                date_absence=date_absence,
                equipe=equipe,
                is_deleted=False,
            )
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise ValidationError(
                    "Une absence existe deja pour cette personne, cette date et cette equipe."
                )
        if effectif and remplacant_effectif and effectif.pk == remplacant_effectif.pk:
            raise ValidationError("Le remplacant doit etre different de la personne absente.")
        if remplacant_effectif and equipe and remplacant_effectif.equipe != equipe:
            raise ValidationError("Le remplacant doit appartenir a la meme equipe.")
        if remplacant_effectif and remplacant:
            raise ValidationError("Choisir un remplacant effectif OU saisir un remplacant externe.")
        if not remplacant_effectif and not remplacant:
            self.add_error("remplacant", "Le remplacant est obligatoire.")
            self.add_error("remplacant_effectif", "Le remplacant est obligatoire.")
        return cleaned


class ModeDegradeForm(forms.ModelForm):
    class Meta:
        model = ModeDegrade
        fields = ["shift", "action", "probleme", "pilote", "date", "cause"]
        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "date-picker-input",
                    "data-open-picker": "true",
                    "autocomplete": "off",
                }
            ),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.statut:
            instance.statut = "Ouvert"
        if not instance.delai:
            instance.delai = instance.date
        if commit:
            instance.save()
        return instance

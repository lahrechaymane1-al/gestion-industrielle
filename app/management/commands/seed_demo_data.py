from __future__ import annotations

from datetime import timedelta
from random import Random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from app.ccb_constants import CCB_OBJECTIF_TOTAL_SHIFT, CCB_OBJECTIFS_HORAIRES
from app.models import (
    Absence,
    AlertePanne,
    ArretBerceau,
    ArretCategory,
    BerceauModule,
    ModeDegrade,
    OperateurEffectif,
    PanneType,
    ProductionBerceau,
    ProductionCCB,
    UserAccessProfile,
)
from app.effectif_team import CANONICAL_CODE_EQUIPE_BY_SCOPE
from app.panne_type_catalog import BERCEAU_PANNE_TYPES, BERCEAU_PANNE_TYPE_NAMES, CCB_PANNE_TYPE_NAMES, CCB_PANNE_TYPES

# Prefixe pour reperer les lignes generees par ce seed (option --reset).
SEED_TAG = "[INIT]"

# Par (equipe, shift): 1 PSP + 5 OPERATEUR, meme ``code_equipe``.
EFFECTIF_CODE_EQUIPE = CANONICAL_CODE_EQUIPE_BY_SCOPE

EFFECTIF_PSP_ROWS = (
    # (cin, equipe, shift, nom_complet, identifiant, num_tel, date_naissance, date_entree, casier, parada)
    (
        "BR25-PSP-A01",
        "Berceau",
        "A",
        "Youssef Alami",
        "MAT-BR-PSP-A",
        "+212662301001",
        "1988-03-22",
        "2014-01-10",
        "CAS-BR-A-PSP",
        "Parada Bab Lakhmis",
    ),
    (
        "BR25-PSP-B01",
        "Berceau",
        "B",
        "Reda Ouazzani",
        "MAT-BR-PSP-B",
        "+212662301002",
        "1987-07-14",
        "2013-06-01",
        "CAS-BR-B-PSP",
        "Parada Hay Hassani",
    ),
    (
        "BR25-PSP-N01",
        "Berceau",
        "N",
        "Hind Benjelloun",
        "MAT-BR-PSP-N",
        "+212662301003",
        "1990-11-08",
        "2015-03-16",
        "CAS-BR-N-PSP",
        "Parada Industrie Nord",
    ),
    (
        "CC25-PSP-A01",
        "CCB",
        "A",
        "Amine El Harti",
        "MAT-CC-PSP-A",
        "+212662302001",
        "1989-05-30",
        "2014-09-01",
        "CAS-CC-A-PSP",
        "Parada CCB Zone A",
    ),
    (
        "CC25-PSP-B01",
        "CCB",
        "B",
        "Othman Idrissi",
        "MAT-CC-PSP-B",
        "+212662302002",
        "1991-01-19",
        "2016-04-12",
        "CAS-CC-B-PSP",
        "Parada CCB Zone B",
    ),
    (
        "CC25-PSP-N01",
        "CCB",
        "N",
        "Lamiae Amrani",
        "MAT-CC-PSP-N",
        "+212662302003",
        "1992-08-25",
        "2017-01-08",
        "CAS-CC-N-PSP",
        "Parada CCB Nuit",
    ),
)

# 5 operateurs par equipe/shift: (cin, identifiant, nom_complet, sexe, tel, d_naiss, d_entree, casier, parada, specialite)
EFFECTIF_OPERATEURS = {
    ("Berceau", "A"): (
        ("BRC-A25-0301", "MAT-BR-A-101", "Anas Benkhadra", "Homme", "+212662311011", "1993-02-10", "2017-03-01", "A-214", "Parada Bab Lakhmis", "Montage ligne"),
        ("BRC-A25-0302", "MAT-BR-A-102", "Sara El Mansouri", "Femme", "+212662311012", "1995-09-21", "2018-01-15", "A-218", "Parada Hay Hassani", "Controle qualite"),
        ("BRC-A25-0303", "MAT-BR-A-103", "Mehdi Tazi", "Homme", "+212662311013", "1994-06-05", "2017-09-01", "A-221", "Parada Industrie Nord", "Assemblage"),
        ("BRC-A25-0304", "MAT-BR-A-104", "Imane Cherkaoui", "Femme", "+212662311014", "1996-12-18", "2019-04-22", "A-225", "Parada Bab Lakhmis", "Logistique ligne"),
        ("BRC-A25-0305", "MAT-BR-A-105", "Khalid Fassi", "Homme", "+212662311015", "1992-04-30", "2016-11-07", "A-229", "Parada Hay Hassani", "Retouches"),
    ),
    ("Berceau", "B"): (
        ("BRC-B25-0301", "MAT-BR-B-101", "Hamza Berrada", "Homme", "+212662312011", "1991-08-14", "2015-02-01", "B-114", "Parada Bab Lakhmis", "Montage ligne"),
        ("BRC-B25-0302", "MAT-BR-B-102", "Fatima Zahra El Ouafi", "Femme", "+212662312012", "1994-03-27", "2018-06-10", "B-118", "Parada Hay Hassani", "Assemblage"),
        ("BRC-B25-0303", "MAT-BR-B-103", "Omar Sebti", "Homme", "+212662312013", "1993-11-09", "2017-01-20", "B-121", "Parada Industrie Nord", "Controle visuel"),
        ("BRC-B25-0304", "MAT-BR-B-104", "Nadia Kettani", "Femme", "+212662312014", "1995-01-02", "2019-03-05", "B-125", "Parada Bab Lakhmis", "Magasin piece"),
        ("BRC-B25-0305", "MAT-BR-B-105", "Yassine Amzil", "Homme", "+212662312015", "1992-10-16", "2016-08-14", "B-129", "Parada Hay Hassani", "Montage ligne"),
    ),
    ("Berceau", "N"): (
        ("BRC-N25-0301", "MAT-BR-N-101", "Adil Chakir", "Homme", "+212662313011", "1990-05-20", "2014-10-01", "N-314", "Parada Industrie Nord", "Equipe nuit montage"),
        ("BRC-N25-0302", "MAT-BR-N-102", "Salma Rami", "Femme", "+212662313012", "1993-07-11", "2017-02-13", "N-318", "Parada Hay Hassani", "Etiquetage"),
        ("BRC-N25-0303", "MAT-BR-N-103", "Bilal Ziani", "Homme", "+212662313013", "1994-12-03", "2018-05-22", "N-321", "Parada Bab Lakhmis", "Assemblage"),
        ("BRC-N25-0304", "MAT-BR-N-104", "Hajar Benkirane", "Femme", "+212662313014", "1996-04-25", "2019-09-09", "N-325", "Parada Industrie Nord", "Controle nuit"),
        ("BRC-N25-0305", "MAT-BR-N-105", "Rachid El Mouden", "Homme", "+212662313015", "1991-09-17", "2015-12-01", "N-329", "Parada Hay Hassani", "Maintenance 1er niveau"),
    ),
    ("CCB", "A"): (
        ("CCB-A25-0401", "MAT-CC-A-101", "Karim Sabri", "Homme", "+212662321011", "1992-01-08", "2016-04-01", "CCB-A-01", "Parada CCB Zone A", "Chaine A"),
        ("CCB-A25-0402", "MAT-CC-A-102", "Leila Mernissi", "Femme", "+212662321012", "1994-06-30", "2018-02-12", "CCB-A-02", "Parada CCB Zone A", "Preparation"),
        ("CCB-A25-0403", "MAT-CC-A-103", "Hicham Daoudi", "Homme", "+212662321013", "1993-03-15", "2017-07-20", "CCB-A-03", "Parada CCB Zone B", "Montage"),
        ("CCB-A25-0404", "MAT-CC-A-104", "Ghita Alaoui", "Femme", "+212662321014", "1995-10-22", "2019-05-06", "CCB-A-04", "Parada CCB Zone A", "Qualite"),
        ("CCB-A25-0405", "MAT-CC-A-105", "Soufiane Tadlaoui", "Homme", "+212662321015", "1991-12-11", "2015-11-18", "CCB-A-05", "Parada CCB Nuit", "Manutention"),
    ),
    ("CCB", "B"): (
        ("CCB-B25-0401", "MAT-CC-B-101", "Mustapha El Filali", "Homme", "+212662322011", "1990-02-28", "2014-08-01", "CCB-B-01", "Parada CCB Zone B", "Chaine B"),
        ("CCB-B25-0402", "MAT-CC-B-102", "Kawtar Benani", "Femme", "+212662322012", "1993-05-09", "2017-03-14", "CCB-B-02", "Parada CCB Zone A", "Assemblage"),
        ("CCB-B25-0403", "MAT-CC-B-103", "Driss El Hajji", "Homme", "+212662322013", "1994-09-01", "2018-10-22", "CCB-B-03", "Parada CCB Zone B", "Reglage"),
        ("CCB-B25-0404", "MAT-CC-B-104", "Meryem Sbai", "Femme", "+212662322014", "1996-01-14", "2019-01-28", "CCB-B-04", "Parada CCB Zone B", "Controle"),
        ("CCB-B25-0405", "MAT-CC-B-105", "Jaouad Kabbaj", "Homme", "+212662322015", "1992-07-07", "2016-06-06", "CCB-B-05", "Parada CCB Zone A", "Expedition"),
    ),
    ("CCB", "N"): (
        ("CCB-N25-0401", "MAT-CC-N-101", "Abdelali Rhani", "Homme", "+212662323011", "1989-11-30", "2013-12-01", "CCB-N-01", "Parada CCB Nuit", "Nuit chaine"),
        ("CCB-N25-0402", "MAT-CC-N-102", "Ilham Bensalah", "Femme", "+212662323012", "1992-04-04", "2016-09-09", "CCB-N-02", "Parada CCB Zone B", "Etiquetage nuit"),
        ("CCB-N25-0403", "MAT-CC-N-103", "Zakaria El Khaldi", "Homme", "+212662323013", "1993-08-18", "2017-11-11", "CCB-N-03", "Parada CCB Nuit", "Montage nuit"),
        ("CCB-N25-0404", "MAT-CC-N-104", "Samira Tazi", "Femme", "+212662323014", "1995-02-25", "2018-04-04", "CCB-N-04", "Parada CCB Zone A", "Qualite nuit"),
        ("CCB-N25-0405", "MAT-CC-N-105", "Noureddine Amrani", "Homme", "+212662323015", "1991-06-06", "2015-05-15", "CCB-N-05", "Parada CCB Nuit", "Maintenance nuit"),
    ),
}


class Command(BaseCommand):
    help = "Charge les donnees initiales (effectif, production, arrets, etc.) — idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14, help="Number of days to seed.")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les lignes marquees [INIT] ou [DEMO] puis les productions sur la periode avant re-seed.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        days = max(3, int(options["days"]))
        reset = bool(options["reset"])
        rng = Random(20260428)
        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)

        users = self._ensure_seed_users()
        effectifs = self._ensure_seed_effectifs(users)

        if reset:
            self._reset_seed_rows(start_date)

        self._ensure_reference_data(users["admin"])
        self._seed_production_berceau(start_date, days, rng)
        self._seed_production_ccb(start_date, days, rng)
        self._seed_arrets_and_alertes(start_date, days, rng, users["ru"])
        self._seed_absences(start_date, days, rng, effectifs["all"], users["ru"])
        self._seed_mode_degrade(start_date, days, rng, users["ru"])

        self.stdout.write(
            self.style.SUCCESS(
                "Donnees initiales chargees. Effectif: Berceau et CCB, shifts A/B/N — chaque shift 1 PSP + 5 operateurs "
                "(meme code equipe); production / arrets / absences / mode degrade."
            )
        )
        self.stdout.write(
            "Comptes (identifiant = nom d'utilisateur, code = mot de passe) :\n"
            "  Admin: admin_si / AdminSi2026!\n"
            "  RU:    ru_atelier / RuAtelier2026!\n"
            "  PSP Berceau: br_psp_a / BrPsp2026-A! | br_psp_b / BrPsp2026-B! | br_psp_n / BrPsp2026-N!\n"
            "  PSP CCB:     ccb_psp_a / CcbPsp2026-A! | ccb_psp_b / CcbPsp2026-B! | ccb_psp_n / CcbPsp2026-N!\n"
            "Synchronisation shift: changement de shift du PSP aligne l'equipe (meme code equipe, sinon psp_lead)."
        )

    def _ensure_seed_users(self):
        User = get_user_model()
        admin, _ = User.objects.get_or_create(
            username="admin_si",
            defaults={"is_staff": True, "is_superuser": True},
        )
        admin.set_password("AdminSi2026!")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=["password", "is_staff", "is_superuser"])

        ru, _ = User.objects.get_or_create(username="ru_atelier", defaults={"is_staff": True})
        ru.set_password("RuAtelier2026!")
        ru.is_staff = True
        ru.save(update_fields=["password", "is_staff"])

        br_psp_a, _ = User.objects.get_or_create(username="br_psp_a")
        br_psp_b, _ = User.objects.get_or_create(username="br_psp_b")
        br_psp_n, _ = User.objects.get_or_create(username="br_psp_n")
        br_psp_a.set_password("BrPsp2026-A!")
        br_psp_b.set_password("BrPsp2026-B!")
        br_psp_n.set_password("BrPsp2026-N!")
        br_psp_a.save(update_fields=["password"])
        br_psp_b.save(update_fields=["password"])
        br_psp_n.save(update_fields=["password"])

        ccb_psp_a, _ = User.objects.get_or_create(username="ccb_psp_a")
        ccb_psp_b, _ = User.objects.get_or_create(username="ccb_psp_b")
        ccb_psp_n, _ = User.objects.get_or_create(username="ccb_psp_n")
        ccb_psp_a.set_password("CcbPsp2026-A!")
        ccb_psp_b.set_password("CcbPsp2026-B!")
        ccb_psp_n.set_password("CcbPsp2026-N!")
        ccb_psp_a.save(update_fields=["password"])
        ccb_psp_b.save(update_fields=["password"])
        ccb_psp_n.save(update_fields=["password"])
        return {
            "admin": admin,
            "ru": ru,
            "br_psp_a": br_psp_a,
            "br_psp_b": br_psp_b,
            "br_psp_n": br_psp_n,
            "ccb_psp_a": ccb_psp_a,
            "ccb_psp_b": ccb_psp_b,
            "ccb_psp_n": ccb_psp_n,
        }

    def _ensure_seed_effectifs(self, users):
        base_common = {
            "type_contrat": "CDI",
            "niveau_etude": "Bac professionnel",
            "pointure_chaussure": 42,
            "taille_pantalon": "M",
            "taille_veste": "L",
            "ville_origine": "Kenitra",
            "ville_actuelle": "Kenitra",
            "updated_by": users["admin"],
        }

        psp_by_equipe_shift: dict[tuple[str, str], OperateurEffectif] = {}
        for row in EFFECTIF_PSP_ROWS:
            (
                cin,
                equipe,
                shift,
                nom_complet,
                identifiant,
                num_tel,
                date_naissance,
                date_entree,
                casier,
                parada,
            ) = row
            squad_code = EFFECTIF_CODE_EQUIPE[(equipe, shift)]
            eff, _ = OperateurEffectif.objects.update_or_create(
                cin=cin,
                defaults={
                    **base_common,
                    "equipe": equipe,
                    "shift": shift,
                    "nom_complet": nom_complet,
                    "identifiant": identifiant,
                    "num_tel": num_tel,
                    "date_naissance": date_naissance,
                    "date_entree": date_entree,
                    "sexe": "Homme",
                    "fonction": "PSP",
                    "psp_lead": None,
                    "code_equipe": squad_code,
                    "is_deleted": False,
                    "numero_casier": casier,
                    "parada_transport": parada,
                    "specialite": "Pilotage equipe et coordination shift",
                },
            )
            psp_by_equipe_shift[(equipe, shift)] = eff

        br_psp_a_eff = psp_by_equipe_shift[("Berceau", "A")]
        br_psp_b_eff = psp_by_equipe_shift[("Berceau", "B")]
        br_psp_n_eff = psp_by_equipe_shift[("Berceau", "N")]
        ccb_psp_a_eff = psp_by_equipe_shift[("CCB", "A")]
        ccb_psp_b_eff = psp_by_equipe_shift[("CCB", "B")]
        ccb_psp_n_eff = psp_by_equipe_shift[("CCB", "N")]

        UserAccessProfile.objects.update_or_create(
            user=users["admin"],
            defaults={"role": UserAccessProfile.Role.ADMIN, "effectif": None},
        )
        UserAccessProfile.objects.update_or_create(
            user=users["ru"],
            defaults={"role": UserAccessProfile.Role.RU, "effectif": None},
        )
        UserAccessProfile.objects.update_or_create(
            user=users["br_psp_a"],
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": br_psp_a_eff},
        )
        UserAccessProfile.objects.update_or_create(
            user=users["br_psp_b"],
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": br_psp_b_eff},
        )
        UserAccessProfile.objects.update_or_create(
            user=users["br_psp_n"],
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": br_psp_n_eff},
        )
        UserAccessProfile.objects.update_or_create(
            user=users["ccb_psp_a"],
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": ccb_psp_a_eff},
        )
        UserAccessProfile.objects.update_or_create(
            user=users["ccb_psp_b"],
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": ccb_psp_b_eff},
        )
        UserAccessProfile.objects.update_or_create(
            user=users["ccb_psp_n"],
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": ccb_psp_n_eff},
        )

        for (equipe, shift), roster in EFFECTIF_OPERATEURS.items():
            psp_eff = psp_by_equipe_shift[(equipe, shift)]
            squad_code = EFFECTIF_CODE_EQUIPE[(equipe, shift)]
            for (
                ocin,
                oid,
                onom,
                osexe,
                otel,
                onaiss,
                oentree,
                ocasier,
                oparada,
                ospec,
            ) in roster:
                OperateurEffectif.objects.update_or_create(
                    cin=ocin,
                    defaults={
                        **base_common,
                        "equipe": equipe,
                        "shift": shift,
                        "nom_complet": onom,
                        "identifiant": oid,
                        "num_tel": otel,
                        "date_naissance": onaiss,
                        "date_entree": oentree,
                        "sexe": osexe,
                        "fonction": "OPERATEUR",
                        "numero_casier": ocasier,
                        "parada_transport": oparada,
                        "specialite": ospec,
                        "psp_lead": psp_eff,
                        "code_equipe": squad_code,
                        "is_deleted": False,
                    },
                )

        # Anciennes fiches seed (CIN prefixe DEMO-): archive pour eviter doublons et comptes obsoletes.
        OperateurEffectif.objects.filter(cin__startswith="DEMO-", is_deleted=False).update(is_deleted=True)

        legacy_psp_users = {
            "psp_berceau_a": ("Berceau", "A", br_psp_a_eff),
            "psp_berceau_b": ("Berceau", "B", br_psp_b_eff),
            "psp_berceau_n": ("Berceau", "N", br_psp_n_eff),
            "psp_ccb_a": ("CCB", "A", ccb_psp_a_eff),
            "psp_ccb_b": ("CCB", "B", ccb_psp_b_eff),
            "psp_ccb_n": ("CCB", "N", ccb_psp_n_eff),
        }
        User = get_user_model()
        for legacy_username, (_eq, _sh, eff_row) in legacy_psp_users.items():
            legacy_user = User.objects.filter(username=legacy_username).first()
            if legacy_user:
                UserAccessProfile.objects.update_or_create(
                    user=legacy_user,
                    defaults={"role": UserAccessProfile.Role.PSP, "effectif": eff_row},
                )
        # Comptes obsoletes sans mapping shift (psp_a / psp_b / psp_n generiques).
        UserAccessProfile.objects.filter(user__username__in=["psp_a", "psp_b", "psp_n"]).delete()

        all_effectifs = list(
            OperateurEffectif.objects.filter(equipe__in=["Berceau", "CCB"], is_deleted=False).order_by("id")[:48]
        )
        return {"all": all_effectifs}

    def _ensure_reference_data(self, admin_user):
        if not BerceauModule.objects.exists():
            self.stdout.write("No Berceau matrix found. Run seed_berceau_matrix first.")

        for name in BERCEAU_PANNE_TYPES:
            PanneType.objects.update_or_create(
                name=name,
                defaults={"description": "", "is_active": True, "updated_by": admin_user},
            )
        for name in CCB_PANNE_TYPES:
            PanneType.objects.update_or_create(
                name=name,
                defaults={"description": "", "is_active": True, "updated_by": admin_user},
            )

    def _seed_production_berceau(self, start_date, days, rng: Random):
        shifts = ["A", "B", "N"]
        lines = ["A1", "A3"]
        for d in range(days):
            day = start_date + timedelta(days=d)
            for shift in shifts:
                for line in lines:
                    objectifs = [80 + rng.randint(0, 30) for _ in range(8)]
                    productions = [max(0, obj - rng.randint(0, 25)) for obj in objectifs]
                    rebut = [rng.randint(0, 4) for _ in range(8)]
                    retouche = [rng.randint(0, 3) for _ in range(8)]
                    defaults = {
                        "objectif": sum(objectifs),
                        **{f"objectif_h{i+1}": objectifs[i] for i in range(8)},
                        **{f"production_h{i+1}": productions[i] for i in range(8)},
                        **{f"rebut_h{i+1}": rebut[i] for i in range(8)},
                        **{f"retouche_h{i+1}": retouche[i] for i in range(8)},
                        **{f"line_h{i+1}": line for i in range(8)},
                        "validated_hours_mask": (1 << rng.randint(3, 8)) - 1,
                    }
                    ProductionBerceau.objects.update_or_create(
                        line=line,
                        date=day,
                        shift=shift,
                        defaults=defaults,
                    )

    def _seed_production_ccb(self, start_date, days, rng: Random):
        for d in range(days):
            day = start_date + timedelta(days=d)
            for shift in ["A", "B", "N"]:
                productions = [rng.randint(0, max(0, int(CCB_OBJECTIFS_HORAIRES[i]) - 3)) for i in range(8)]
                rebuts = [rng.randint(0, min(4, productions[i])) for i in range(8)]
                obj, _ = ProductionCCB.objects.update_or_create(
                    date=day,
                    shift=shift,
                    defaults={
                        "objectif": CCB_OBJECTIF_TOTAL_SHIFT,
                        **{f"production_h{i+1}": productions[i] for i in range(8)},
                        **{f"rebut_h{i+1}": rebuts[i] for i in range(8)},
                        "retouche": 0,
                        "temps_arrets": 0,
                    },
                )
                obj.save()

    def _seed_arrets_and_alertes(self, start_date, days, rng: Random, user):
        modules = list(BerceauModule.objects.filter(is_active=True).exclude(name="CCB")[:3])
        if not modules:
            return
        panne_types = list(PanneType.objects.filter(is_active=True))
        berceau_panne_types = [pt for pt in panne_types if pt.name in BERCEAU_PANNE_TYPE_NAMES]
        ccb_panne_types = [pt for pt in panne_types if pt.name in CCB_PANNE_TYPE_NAMES]
        ccb_module = BerceauModule.objects.filter(name="CCB", is_active=True).first()
        ccb_postes = list(ccb_module.postes.filter(is_active=True)) if ccb_module else []
        for d in range(days):
            day = start_date + timedelta(days=d)
            for shift in ["A", "B", "N"]:
                for hour in range(1, 9):
                    category = [
                        ArretCategory.MAINTENANCE,
                        ArretCategory.KTA,
                        ArretCategory.LOGISTIQUE,
                        ArretCategory.FABRICATION,
                    ][(d + hour) % 4]
                    module = modules[(d + hour) % len(modules)]
                    postes = list(module.postes.filter(is_active=True))
                    if not postes:
                        continue
                    poste = postes[(hour - 1) % len(postes)]
                    moyens = list(poste.moyens.filter(is_active=True))
                    if not moyens:
                        continue
                    moyen = moyens[(d + hour) % len(moyens)]
                    ArretBerceau.objects.update_or_create(
                        module=module,
                        poste=poste,
                        moyen=moyen,
                        date=day,
                        shift=shift,
                        heure_production=hour,
                        defaults={
                            "temps_arret_min": rng.randint(0, 15),
                            "category": category,
                            "commentaire": f"{SEED_TAG} Arret {shift} H{hour}",
                            "updated_by": user,
                        },
                    )
                    if not berceau_panne_types:
                        continue
                    AlertePanne.objects.create(
                        module=module,
                        poste=poste,
                        moyen=moyen,
                        panne_type=berceau_panne_types[(d + hour) % len(berceau_panne_types)],
                        cause=f"{SEED_TAG} Cause {shift}-{hour}",
                        solution=f"{SEED_TAG} Solution {shift}-{hour}",
                        category=category,
                        date=day,
                        shift=shift,
                        heure_production=hour,
                        temps_arret_min=rng.randint(1, 12),
                        equipe="Berceau",
                        updated_by=user,
                    )

                    if not (ccb_module and ccb_postes and ccb_panne_types):
                        continue
                    cp = ccb_postes[(hour - 1) % len(ccb_postes)]
                    cms = list(cp.moyens.filter(is_active=True))
                    if not cms:
                        continue
                    cm = cms[(d + hour) % len(cms)]
                    AlertePanne.objects.create(
                        module=ccb_module,
                        poste=cp,
                        moyen=cm,
                        panne_type=ccb_panne_types[(d + hour) % len(ccb_panne_types)],
                        cause=f"{SEED_TAG} CCB cause {shift} H{hour}",
                        solution=f"{SEED_TAG} CCB solution {shift} H{hour}",
                        category=category,
                        date=day,
                        shift=shift,
                        heure_production=hour,
                        temps_arret_min=rng.randint(1, 14),
                        equipe="CCB",
                        updated_by=user,
                    )

    def _seed_absences(self, start_date, days, rng: Random, effectifs, user):
        if len(effectifs) < 3:
            return
        for d in range(0, days, 3):
            day = start_date + timedelta(days=d)
            absent = effectifs[d % len(effectifs)]
            remp = effectifs[(d + 1) % len(effectifs)]
            Absence.objects.update_or_create(
                effectif=absent,
                date_absence=day,
                equipe=absent.equipe,
                defaults={
                    "remplacant_effectif": remp if remp.id != absent.id else None,
                    "shift": absent.shift,
                    "motif": "Conge planifie",
                    "remplacant": "" if remp.id != absent.id else "Remplacant externe",
                    "nom_complet": absent.nom_complet,
                    "commentaire": f"{SEED_TAG} Absence planifiee",
                    "updated_by": user,
                    "is_deleted": False,
                },
            )

    def _seed_mode_degrade(self, start_date, days, rng: Random, user):
        for d in range(0, days, 2):
            day = start_date + timedelta(days=d)
            for equipe in ["Berceau", "CCB"]:
                shift = ["A", "B", "N"][d % 3]
                ModeDegrade.objects.create(
                    equipe=equipe,
                    shift=shift,
                    action=f"{SEED_TAG} Action {equipe} {shift}",
                    probleme=f"{SEED_TAG} Probleme {rng.randint(1, 9)}",
                    pilote="Chef UEP",
                    date=day,
                    delai=day + timedelta(days=2),
                    cause="Analyse cause (donnees initiales)",
                    statut=["Ouvert", "En cours", "Clos"][d % 3],
                    updated_by=user,
                    is_deleted=False,
                )

    def _reset_seed_rows(self, start_date):
        tag_filter = Q(cause__startswith="[DEMO]") | Q(cause__startswith=SEED_TAG)
        AlertePanne.objects.filter(tag_filter).delete()
        cmt_filter = Q(commentaire__startswith="[DEMO]") | Q(commentaire__startswith=SEED_TAG)
        ArretBerceau.objects.filter(cmt_filter).delete()
        Absence.objects.filter(cmt_filter).delete()
        act_filter = Q(action__startswith="[DEMO]") | Q(action__startswith=SEED_TAG)
        ModeDegrade.objects.filter(act_filter).delete()
        ProductionBerceau.objects.filter(date__gte=start_date).delete()
        ProductionCCB.objects.filter(date__gte=start_date).delete()

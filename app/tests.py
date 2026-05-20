import json
from datetime import date
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils.crypto import get_random_string

from .models import Absence, ModeDegrade, OperateurEffectif, ProductionBerceau, UserAccessProfile
from stock.models import StockJournal
from .downtime_impact import (
    berceau_alerte_impact_pct,
    downtime_impact_percent,
    hourly_objective_for_diversity,
    parse_diversite_from_cause,
    resolve_diversity_for_impact,
    total_objectif_for_diversity,
)


class AuthenticationFlowTests(TestCase):
    def test_protected_page_redirects_to_login_when_logged_out(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

    def test_login_with_invalid_credentials_shows_error(self):
        response = self.client.post(
            reverse("login"),
            data={"identifiant": "wrong", "code": "wrong"},
            follow=True,
        )
        self.assertContains(response, "Identifiants incorrects.")

    def test_first_login_bootstrap_creates_admin_user(self):
        response = self.client.post(
            reverse("login"),
            data={"identifiant": "admin", "code": "admin12345"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("react_app"))

        User = get_user_model()
        user = User.objects.get(username="admin")
        self.assertTrue(user.is_superuser)


class ProductionExportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="strong-pass-123")
        self.client.login(username="tester", password="strong-pass-123")

    def test_excel_export_returns_file_response(self):
        response = self.client.get(reverse("berceau_production_export"), {"format": "excel"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", response["Content-Type"])

    def test_pdf_export_returns_file_response(self):
        response = self.client.get(reverse("berceau_production_export"), {"format": "pdf"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/pdf", response["Content-Type"])

    def test_invalid_export_format_returns_400(self):
        response = self.client.get(reverse("berceau_production_export"), {"format": "csv"})
        self.assertEqual(response.status_code, 400)


class EffectifValidationTests(TestCase):
    def _valid_payload(self):
        return {
            "nom_complet": "Test User",
            "shift": "A",
            "cin": "CD123456",
            "type_contrat": "CDI",
            "date_naissance": "1990-01-01",
            "sexe": "Homme",
            "date_entree": "2010-01-01",
            "identifiant": "EMP-2001",
            "matricule": "MAT-2001",
            "num_tel": "+212612345678",
            "fonction": "OPERATEUR",
            "ville_actuelle": "Casablanca",
            "niveau_etude": "Bac",
            "numero_casier": "A1",
            "parada_transport": "Parada A",
            "pointure_chaussure": 42,
            "specialite": "Montage",
            "taille_pantalon": "M",
            "taille_veste": "L",
            "ville_origine": "Rabat",
            "equipe": "Berceau",
        }

    def test_invalid_phone_raises_validation(self):
        payload = self._valid_payload()
        payload["num_tel"] = "not-a-phone"
        obj = OperateurEffectif(**payload)
        with self.assertRaises(ValidationError):
            obj.full_clean()

    def test_invalid_contrat_raises_validation(self):
        payload = self._valid_payload()
        payload["type_contrat"] = "XYZ"
        obj = OperateurEffectif(**payload)
        with self.assertRaises(ValidationError):
            obj.full_clean()

    def test_entry_date_before_minimum_age_raises_validation(self):
        payload = self._valid_payload()
        payload["date_naissance"] = "2010-01-01"
        payload["date_entree"] = "2020-01-01"
        obj = OperateurEffectif(**payload)
        with self.assertRaises(ValidationError):
            obj.full_clean()


class EffectifApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username="apiadmin", password="strong-pass-123")
        self.client.login(username="apiadmin", password="strong-pass-123")

    def _payload(self):
        return {
            "nom_complet": "API User",
            "shift": "A",
            "cin": "EF123456",
            "type_contrat": "CDI",
            "date_naissance": "1990-01-01",
            "sexe": "Homme",
            "date_entree": "2010-01-01",
            "identifiant": "EMP-3001",
            "matricule": "MAT-3001",
            "num_tel": "+212612345678",
            "fonction": "OPERATEUR",
            "ville_actuelle": "Fes",
            "niveau_etude": "Bac",
            "numero_casier": "B2",
            "parada_transport": "Parada B",
            "pointure_chaussure": 41,
            "specialite": "Qualite",
            "taille_pantalon": "M",
            "taille_veste": "L",
            "ville_origine": "Meknes",
            "equipe": "Berceau",
            "code_equipe": "",
        }

    def test_effectif_api_crud_and_uniqueness(self):
        import json

        create_response = self.client.post(
            reverse("api_effectifs"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        created_id = create_response.json()["id"]

        list_response = self.client.get(reverse("api_effectifs"), {"q": "API User"})
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(list_response.json()["total"], 1)

        detail_response = self.client.get(reverse("api_effectif_detail", kwargs={"pk": created_id}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["cin"], "EF123456")

        duplicate_response = self.client.post(
            reverse("api_effectifs"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(duplicate_response.status_code, 400)

        patch_payload = self._payload()
        patch_payload["nom_complet"] = "API User Updated"
        patch_payload["cin"] = "EF123457"
        patch_payload["identifiant"] = "EMP-3002"
        update_response = self.client.put(
            reverse("api_effectif_detail", kwargs={"pk": created_id}),
            data=json.dumps(patch_payload),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)

        delete_response = self.client.delete(reverse("api_effectif_detail", kwargs={"pk": created_id}))
        self.assertEqual(delete_response.status_code, 200)

    def test_psp_shift_update_syncs_team_shift(self):
        import json

        User = get_user_model()
        psp_user = User.objects.create_user(username="psp_sync_u", password="strong-pass-123")
        psp_effectif = OperateurEffectif.objects.create(
            nom_complet="PSP Sync",
            shift="A",
            cin="PSP-SYNC-1",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="PSP-SYNC-1",
            num_tel="+212611111111",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
            code_equipe="SYNC-CODE-1",
        )
        UserAccessProfile.objects.create(user=psp_user, role=UserAccessProfile.Role.PSP, effectif=psp_effectif)
        op = OperateurEffectif.objects.create(
            nom_complet="Operateur Sync",
            shift="A",
            cin="OP-SYNC-1",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant="OP-SYNC-1",
            num_tel="+212622222222",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X2",
            parada_transport="P2",
            pointure_chaussure=41,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
            psp_lead=psp_effectif,
            code_equipe="SYNC-CODE-1",
        )
        payload = self._payload()
        payload.update(
            {
                "nom_complet": "PSP Sync",
                "cin": "PSP-SYNC-1",
                "identifiant": "PSP-SYNC-1",
                "fonction": "PSP",
                "shift": "B",
                "code_equipe": "SYNC-CODE-1",
            }
        )
        res = self.client.patch(
            reverse("api_effectif_detail", kwargs={"pk": psp_effectif.id}),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        op.refresh_from_db()
        self.assertEqual(op.shift, "B")
        self.assertEqual(res.json().get("team_shift_updated_count"), 1)

    def test_psp_shift_update_moves_team_linked_by_psp_lead(self):
        """Changement de shift PSP : seuls les operateurs avec psp_lead sur ce PSP suivent (pas via code_equipe)."""
        import json

        psp_effectif = OperateurEffectif.objects.create(
            nom_complet="PSP Canon",
            shift="A",
            cin="PSP-CANON-1",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="PSP-CANON-1",
            num_tel="+212611111113",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
            code_equipe="BER-EQ-A",
        )
        op = OperateurEffectif.objects.create(
            nom_complet="Op Canon",
            shift="A",
            cin="OP-CANON-1",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant="OP-CANON-1",
            num_tel="+212622222224",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X2",
            parada_transport="P2",
            pointure_chaussure=41,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
            psp_lead=psp_effectif,
            code_equipe="BER-EQ-A",
        )
        payload = self._payload()
        payload.update(
            {
                "nom_complet": "PSP Canon",
                "cin": "PSP-CANON-1",
                "identifiant": "PSP-CANON-1",
                "fonction": "PSP",
                "shift": "B",
                "code_equipe": "BER-EQ-A",
            }
        )
        res = self.client.patch(
            reverse("api_effectif_detail", kwargs={"pk": psp_effectif.id}),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        psp_effectif.refresh_from_db()
        op.refresh_from_db()
        self.assertEqual(psp_effectif.shift, "B")
        self.assertEqual(op.shift, "B")
        self.assertEqual(op.psp_lead_id, psp_effectif.id)
        # code_equipe n'est plus synchronise automatiquement
        self.assertEqual(psp_effectif.code_equipe, "BER-EQ-A")
        self.assertEqual(op.code_equipe, "BER-EQ-A")

    def test_admin_can_set_psp_linked_username_on_patch(self):
        import json

        User = get_user_model()
        login_user = User.objects.create_user(username="psp_account_z", password="secret-123")

        psp_effectif = OperateurEffectif.objects.create(
            nom_complet="PSP ACCT",
            shift="A",
            cin="PSP-ACCT-1",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="PSP-ACCT-1",
            num_tel="+212611111114",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
        )
        payload = self._payload()
        payload.update(
            {
                "nom_complet": "PSP ACCT",
                "cin": "PSP-ACCT-1",
                "identifiant": "PSP-ACCT-1",
                "fonction": "PSP",
                "psp_linked_username": "psp_account_z",
            }
        )
        res = self.client.patch(
            reverse("api_effectif_detail", kwargs={"pk": psp_effectif.id}),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        prof = UserAccessProfile.objects.get(user=login_user)
        self.assertEqual(prof.role, UserAccessProfile.Role.PSP)
        self.assertEqual(prof.effectif_id, psp_effectif.id)

        detail = self.client.get(reverse("api_effectif_detail", kwargs={"pk": psp_effectif.id}))
        self.assertEqual(detail.json().get("psp_linked_username"), "psp_account_z")

    def test_psp_shift_update_does_not_move_unlinked_same_shift_operators(self):
        """Operateur meme shift sans psp_lead ne suit pas le changement de shift du PSP."""
        import json

        psp_effectif = OperateurEffectif.objects.create(
            nom_complet="PSP Unlinked",
            shift="A",
            cin="PSP-UNLINK-1",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="PSP-UNLINK-1",
            num_tel="+212611111115",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
            code_equipe="LEGACY-CODE",
        )
        linked = OperateurEffectif.objects.create(
            nom_complet="Op lie",
            shift="A",
            cin="OP-LINK-1",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant="OP-LINK-1",
            num_tel="+212622222225",
            sexe="Homme",
            fonction="OPERATEUR",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X2",
            parada_transport="P2",
            pointure_chaussure=41,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
            psp_lead=psp_effectif,
            code_equipe="LEGACY-CODE",
        )
        orphan = OperateurEffectif.objects.create(
            nom_complet="Op sans lead",
            shift="A",
            cin="OP-ORPH-1",
            type_contrat="CDI",
            date_naissance="1992-01-01",
            date_entree="2012-01-01",
            identifiant="OP-ORPH-1",
            num_tel="+212622222226",
            sexe="Homme",
            fonction="OPERATEUR",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X3",
            parada_transport="P3",
            pointure_chaussure=40,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
            psp_lead=None,
            code_equipe="LEGACY-CODE",
        )
        payload = self._payload()
        payload.update(
            {
                "nom_complet": "PSP Unlinked",
                "cin": "PSP-UNLINK-1",
                "identifiant": "PSP-UNLINK-1",
                "fonction": "PSP",
                "shift": "N",
            }
        )
        res = self.client.patch(
            reverse("api_effectif_detail", kwargs={"pk": psp_effectif.id}),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        linked.refresh_from_db()
        orphan.refresh_from_db()
        self.assertEqual(linked.shift, "N")
        self.assertEqual(orphan.shift, "A")
        self.assertEqual(res.json().get("team_shift_updated_count"), 1)

    def test_psp_list_shows_only_psp_lead_team(self):
        """Liste effectif PSP : fiche PSP + operateurs avec psp_lead, pas les autres du shift."""
        User = get_user_model()
        psp_u = User.objects.create_user(username="psp_ccb_b_test", password="psp-pass-team")
        psp_row = OperateurEffectif.objects.create(
            nom_complet="PSP CCB B Test",
            shift="B",
            cin="PSP-CCB-B-T",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="MAT-CC-PSP-B-TEST",
            num_tel="+212611111116",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Kenitra",
            equipe="CCB",
        )
        UserAccessProfile.objects.create(
            user=psp_u, role=UserAccessProfile.Role.PSP, effectif=psp_row
        )
        in_team = OperateurEffectif.objects.create(
            nom_complet="Dans equipe",
            shift="B",
            cin="OP-IN-TEAM",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant="OP-IN-TEAM-ID",
            num_tel="+212622222227",
            sexe="Homme",
            fonction="OPERATEUR",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C2",
            parada_transport="P2",
            pointure_chaussure=41,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Kenitra",
            equipe="CCB",
            psp_lead=psp_row,
        )
        same_shift_no_lead = OperateurEffectif.objects.create(
            nom_complet="Hors equipe",
            shift="B",
            cin="OP-NO-LEAD",
            type_contrat="CDI",
            date_naissance="1992-01-01",
            date_entree="2012-01-01",
            identifiant="OP-NO-LEAD-ID",
            num_tel="+212622222228",
            sexe="Homme",
            fonction="OPERATEUR",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C3",
            parada_transport="P3",
            pointure_chaussure=40,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Kenitra",
            equipe="CCB",
            psp_lead=None,
        )
        other_psp = OperateurEffectif.objects.create(
            nom_complet="Autre PSP",
            shift="B",
            cin="PSP-OTHER-B",
            type_contrat="CDI",
            date_naissance="1988-01-01",
            date_entree="2009-01-01",
            identifiant="PSP-OTHER-B-ID",
            num_tel="+212622222229",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C4",
            parada_transport="P4",
            pointure_chaussure=43,
            specialite="Pilotage",
            taille_pantalon="L",
            taille_veste="XL",
            ville_origine="Kenitra",
            equipe="CCB",
        )
        wrong_lead = OperateurEffectif.objects.create(
            nom_complet="Autre lead",
            shift="B",
            cin="OP-WRONG-LEAD",
            type_contrat="CDI",
            date_naissance="1993-01-01",
            date_entree="2013-01-01",
            identifiant="OP-WRONG-LEAD-ID",
            num_tel="+212622222230",
            sexe="Homme",
            fonction="OPERATEUR",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C5",
            parada_transport="P5",
            pointure_chaussure=39,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Kenitra",
            equipe="CCB",
            psp_lead=other_psp,
        )

        self.client.logout()
        self.client.login(username="psp_ccb_b_test", password="psp-pass-team")
        res = self.client.get(reverse("api_effectifs"), {"equipe": "CCB"})
        self.assertEqual(res.status_code, 200)
        ids = {row["id"] for row in res.json().get("results", [])}
        self.assertEqual(ids, {psp_row.id, in_team.id})
        self.assertNotIn(same_shift_no_lead.id, ids)
        self.assertNotIn(wrong_lead.id, ids)
        self.assertNotIn(other_psp.id, ids)

    def test_effectif_rejects_non_psp_lead(self):
        import json

        non_psp = OperateurEffectif.objects.create(
            nom_complet="Non PSP",
            shift="A",
            cin="NON-PSP-1",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant="NON-PSP-1",
            num_tel="+212633333333",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Casa",
            niveau_etude="Bac",
            numero_casier="Y1",
            parada_transport="P3",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Casa",
            equipe="Berceau",
        )
        payload = self._payload()
        payload.update({"cin": "EF999999", "identifiant": "EMP-9999", "psp_lead": non_psp.id})
        res = self.client.post(
            reverse("api_effectifs"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("psp_lead", res.json().get("errors", {}))

    def test_psp_lead_accepts_fonction_psp_without_login_profile(self):
        """Responsable avec fonction PSP sur la fiche, sans compte UserAccessProfile — assignation opérateur possible."""
        import json

        psp_row = OperateurEffectif.objects.create(
            nom_complet="PSP sans compte",
            shift="A",
            cin="PSP-NO-USER-1",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="PSP-NO-USER-1",
            num_tel="+212611111199",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
        )
        payload = self._payload()
        payload.update(
            {
                "cin": "EF888888",
                "identifiant": "EMP-8888",
                "psp_lead": psp_row.id,
            }
        )
        res = self.client.post(
            reverse("api_effectifs"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        created = OperateurEffectif.objects.get(cin="EF888888")
        self.assertEqual(created.psp_lead_id, psp_row.id)
        self.assertEqual(created.shift, "A")

    def test_psp_effectif_list_resolves_lead_via_username_without_profile_fk(self):
        """GET effectifs uses get_psp_effectif_id (username = identifiant), not profile.effectif alone."""
        User = get_user_model()
        username = "MAT-FALLBACK-PSP-LIST"
        psp_u = User.objects.create_user(username=username, password="psp-pass-fblist")
        UserAccessProfile.objects.create(user=psp_u, role=UserAccessProfile.Role.PSP, effectif=None)

        psp_row = OperateurEffectif.objects.create(
            nom_complet="PSP Fallback List",
            shift="B",
            cin="PSP-FB-LIST-1",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=username,
            num_tel="+212611111113",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
        )
        op = OperateurEffectif.objects.create(
            nom_complet="Op sous PSP Fallback",
            shift="B",
            cin="OP-FB-LIST-1",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant="OP-FB-LIST-1-ID",
            num_tel="+212622222224",
            sexe="Homme",
            fonction="OPERATEUR",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="X2",
            parada_transport="P2",
            pointure_chaussure=41,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
            psp_lead=psp_row,
        )

        self.client.logout()
        self.client.login(username=username, password="psp-pass-fblist")
        res = self.client.get(reverse("api_effectifs"), {"equipe": "Berceau"})
        self.assertEqual(res.status_code, 200)
        ids = {row["id"] for row in res.json().get("results", [])}
        self.assertIn(psp_row.id, ids)
        self.assertIn(op.id, ids)

    def test_effectif_shift_change_updates_absence_shift(self):
        import json

        op = OperateurEffectif.objects.create(
            nom_complet="Avec absence",
            shift="A",
            cin="OP-ABS-SHIFT-1",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="OP-ABS-SHIFT-1",
            num_tel="+212612300099",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
        )
        remp = OperateurEffectif.objects.create(
            nom_complet="Remplacant",
            shift="A",
            cin="REM-ABS-1",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="REM-ABS-1",
            num_tel="+212612300088",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Fes",
            niveau_etude="Bac",
            numero_casier="C2",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Fes",
            equipe="Berceau",
        )
        ab = Absence.objects.create(
            equipe="Berceau",
            effectif=op,
            remplacant_effectif=remp,
            shift="A",
            motif="Test sync",
            remplacant="",
            date_absence=date(2025, 6, 1),
        )
        payload = self._payload()
        payload.update(
            {
                "nom_complet": "Avec absence",
                "cin": "OP-ABS-SHIFT-1",
                "identifiant": "OP-ABS-SHIFT-1",
                "shift": "B",
            }
        )
        res = self.client.patch(
            reverse("api_effectif_detail", kwargs={"pk": op.id}),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        ab.refresh_from_db()
        self.assertEqual(ab.shift, "B")


class AbsenceValidationTests(TestCase):
    def setUp(self):
        self.absent = OperateurEffectif.objects.create(
            nom_complet="Collaborateur Test",
            shift="A",
            cin="ABS1001",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="ABS-EMP-1001",
            num_tel="+212612300001",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        self.replacement = OperateurEffectif.objects.create(
            nom_complet="Remplacant Test",
            shift="A",
            cin="ABS1002",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant="ABS-EMP-1002",
            num_tel="+212612300002",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C2",
            parada_transport="P2",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )

    def _valid_payload(self):
        return {
            "equipe": "Berceau",
            "effectif": self.absent,
            "remplacant_effectif": self.replacement,
            "shift": "A",
            "motif": "Maladie",
            "remplacant": "",
            "date_absence": "2026-04-28",
        }

    def test_replacant_must_be_different(self):
        payload = self._valid_payload()
        payload["remplacant_effectif"] = self.absent
        absence = Absence(**payload)
        with self.assertRaises(ValidationError):
            absence.full_clean()

    def test_duplicate_nom_date_equipe_not_allowed(self):
        # The runtime Absence model is unmanaged; enforce duplicate prevention via AbsenceForm validation.
        payload = self._valid_payload()
        Absence.objects.create(**payload)
        from app.forms import AbsenceForm

        form_payload = {
            "effectif": self.absent.id,
            "nom_complet": self.absent.nom_complet,
            "shift": payload["shift"],
            "motif": payload["motif"],
            "date_absence": payload["date_absence"],
            "remplacant_effectif": self.replacement.id,
            "remplacant": "",
            "commentaire": "",
        }
        form = AbsenceForm(form_payload, instance=Absence(equipe="Berceau"))
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_replacant_required(self):
        payload = self._valid_payload()
        payload["remplacant_effectif"] = None
        payload["remplacant"] = ""
        absence = Absence(**payload)
        with self.assertRaises(ValidationError):
            absence.full_clean()

    def test_nom_complet_required_when_no_effectif(self):
        payload = self._valid_payload()
        payload["effectif"] = None
        payload["nom_complet"] = ""
        payload["migration_status"] = "a_corriger"
        absence = Absence(**payload)
        with self.assertRaises(ValidationError):
            absence.full_clean()


class AbsenceApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username="absenceadmin", password="strong-pass-123")
        self.client.login(username="absenceadmin", password="strong-pass-123")
        self.absent = OperateurEffectif.objects.create(
            nom_complet="Absence API",
            shift="A",
            cin="APIABS1001",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="ABS-API-1001",
            num_tel="+212612301001",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Casa",
            niveau_etude="Bac",
            numero_casier="A1",
            parada_transport="P1",
            pointure_chaussure=41,
            specialite="Qualite",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Rabat",
            equipe="Berceau",
        )
        self.replacement = OperateurEffectif.objects.create(
            nom_complet="Operateur Backup",
            shift="A",
            cin="APIABS1002",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant="ABS-API-1002",
            num_tel="+212612301002",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Casa",
            niveau_etude="Bac",
            numero_casier="A2",
            parada_transport="P2",
            pointure_chaussure=41,
            specialite="Qualite",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Rabat",
            equipe="Berceau",
        )

    def _payload(self):
        return {
            "equipe": "Berceau",
            "effectif": self.absent.id,
            "remplacant_effectif": self.replacement.id,
            "shift": "A",
            "motif": "Conge",
            "remplacant": "",
            "date_absence": "2026-05-01",
        }

    def test_absence_api_crud_filters_uniqueness(self):
        import json

        create_response = self.client.post(
            reverse("api_absences"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        created_id = create_response.json()["id"]

        list_response = self.client.get(reverse("api_absences"), {"q": "Absence API"})
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(list_response.json()["total"], 1)

        detail_response = self.client.get(reverse("api_absence_detail", kwargs={"pk": created_id}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["nom_absent"], "Absence API")
        self.assertEqual(detail_response.json()["shift"], "A")

        duplicate_response = self.client.post(
            reverse("api_absences"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(duplicate_response.status_code, 400)

        patch_payload = self._payload()
        patch_payload["motif"] = "Urgence familiale"
        update_response = self.client.patch(
            reverse("api_absence_detail", kwargs={"pk": created_id}),
            data=json.dumps(patch_payload),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)

        delete_response = self.client.delete(reverse("api_absence_detail", kwargs={"pk": created_id}))
        self.assertEqual(delete_response.status_code, 200)

    def test_effectif_options_endpoint(self):
        response = self.client.get(reverse("api_effectif_options"), {"equipe": "Berceau"})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()["results"]), 1)


class PspEffectifBerceauTests(TestCase):
    """PSP Berceau : liste équipe, pas de DELETE, PATCH hors équipe refusé."""

    def setUp(self):
        suffix = get_random_string(8)
        User = get_user_model()
        self.psp_a = OperateurEffectif.objects.create(
            nom_complet=f"PSP Eff A {suffix}",
            shift="A",
            cin=f"PEA{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=f"PSP-EFF-A-{suffix}",
            num_tel="+212612302001",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        self.team_op = OperateurEffectif.objects.create(
            nom_complet=f"Op PSP A {suffix}",
            shift="A",
            cin=f"OPA{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant=f"OP-EFF-A-{suffix}",
            num_tel="+212612302002",
            sexe="Homme",
            fonction="OPERATEUR",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C2",
            parada_transport="P2",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
            psp_lead=self.psp_a,
        )
        self.psp_b = OperateurEffectif.objects.create(
            nom_complet=f"PSP Eff B {suffix}",
            shift="A",
            cin=f"PEB{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=f"PSP-EFF-B-{suffix}",
            num_tel="+212612302003",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C3",
            parada_transport="P3",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        self.other_team_op = OperateurEffectif.objects.create(
            nom_complet=f"Op autre PSP {suffix}",
            shift="A",
            cin=f"OOB{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1992-01-01",
            date_entree="2012-01-01",
            identifiant=f"OP-OTHER-{suffix}",
            num_tel="+212612302004",
            sexe="Homme",
            fonction="OPERATEUR",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C4",
            parada_transport="P4",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
            psp_lead=self.psp_b,
        )
        self.psp_user = User.objects.create_user(username=f"psp_eff_{suffix}", password="strong-pass-123")
        UserAccessProfile.objects.update_or_create(
            user=self.psp_user,
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": self.psp_a},
        )
        self.client.login(username=self.psp_user.username, password="strong-pass-123")

    def _minimal_payload(self, **overrides):
        base = {
            "nom_complet": "Nouvel op",
            "shift": "A",
            "cin": f"NEW{get_random_string(6)}",
            "type_contrat": "CDI",
            "date_naissance": "1990-01-01",
            "sexe": "Homme",
            "date_entree": "2010-01-01",
            "identifiant": f"ID-{get_random_string(6)}",
            "matricule": f"MAT-{get_random_string(4)}",
            "num_tel": "+212612309999",
            "fonction": "OPERATEUR",
            "ville_actuelle": "Kenitra",
            "niveau_etude": "Bac",
            "numero_casier": "C9",
            "parada_transport": "P9",
            "pointure_chaussure": 42,
            "specialite": "Assemblage",
            "taille_pantalon": "M",
            "taille_veste": "L",
            "ville_origine": "Sale",
            "equipe": "Berceau",
        }
        base.update(overrides)
        return base

    def test_psp_list_only_own_team(self):
        response = self.client.get(reverse("api_effectifs"), {"equipe": "Berceau"})
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertIn(self.psp_a.id, ids)
        self.assertIn(self.team_op.id, ids)
        self.assertNotIn(self.other_team_op.id, ids)

    def test_psp_patch_other_team_forbidden(self):
        payload = self._minimal_payload(
            nom_complet=self.other_team_op.nom_complet,
            cin=self.other_team_op.cin,
            identifiant=self.other_team_op.identifiant,
            matricule=self.other_team_op.matricule or "MAT-X",
        )
        response = self.client.put(
            reverse("api_effectif_detail", kwargs={"pk": self.other_team_op.id}),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_psp_delete_forbidden(self):
        response = self.client.delete(reverse("api_effectif_detail", kwargs={"pk": self.team_op.id}))
        self.assertEqual(response.status_code, 403)

    def test_psp_cannot_create_fonction_psp(self):
        payload = self._minimal_payload(fonction="PSP", psp_lead=self.psp_a.id)
        response = self.client.post(
            reverse("api_effectifs"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class PspAbsenceBerceauTests(TestCase):
    """PSP Berceau : liste filtrée équipe/shift, POST hors équipe refusé, pas de DELETE."""

    def setUp(self):
        suffix = get_random_string(8)
        User = get_user_model()
        self.psp_effectif = OperateurEffectif.objects.create(
            nom_complet=f"PSP Absence {suffix}",
            shift="A",
            cin=f"PABS{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=f"PSP-ABS-{suffix}",
            num_tel="+212612301111",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        self.team_op = OperateurEffectif.objects.create(
            nom_complet=f"Operateur PSP {suffix}",
            shift="A",
            cin=f"OABS{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1991-01-01",
            date_entree="2011-01-01",
            identifiant=f"OP-ABS-{suffix}",
            num_tel="+212612301112",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C2",
            parada_transport="P2",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
            psp_lead=self.psp_effectif,
        )
        self.replacement = OperateurEffectif.objects.create(
            nom_complet=f"Backup {suffix}",
            shift="A",
            cin=f"BABS{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1992-01-01",
            date_entree="2012-01-01",
            identifiant=f"BKP-ABS-{suffix}",
            num_tel="+212612301113",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C3",
            parada_transport="P3",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
            psp_lead=self.psp_effectif,
        )
        self.other_shift_op = OperateurEffectif.objects.create(
            nom_complet=f"Shift B {suffix}",
            shift="B",
            cin=f"SB{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1993-01-01",
            date_entree="2013-01-01",
            identifiant=f"SB-ABS-{suffix}",
            num_tel="+212612301114",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C4",
            parada_transport="P4",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        self.psp_user = User.objects.create_user(username=f"psp_abs_{suffix}", password="strong-pass-123")
        UserAccessProfile.objects.update_or_create(
            user=self.psp_user,
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": self.psp_effectif},
        )
        self.absence_team = Absence.objects.create(
            equipe="Berceau",
            effectif=self.team_op,
            remplacant_effectif=self.replacement,
            shift="A",
            motif="Conge",
            remplacant="",
            date_absence=date(2026, 6, 10),
        )
        self.absence_other_shift = Absence.objects.create(
            equipe="Berceau",
            effectif=self.other_shift_op,
            remplacant="Externe B",
            shift="B",
            motif="Maladie",
            date_absence=date(2026, 6, 11),
        )
        self.client.login(username=self.psp_user.username, password="strong-pass-123")

    def test_psp_list_only_own_shift_and_team(self):
        response = self.client.get(reverse("api_absences"), {"equipe": "Berceau"})
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertIn(self.absence_team.id, ids)
        self.assertNotIn(self.absence_other_shift.id, ids)

    def test_psp_post_outside_team_forbidden(self):
        payload = {
            "equipe": "Berceau",
            "effectif": self.other_shift_op.id,
            "remplacant": "Externe",
            "shift": "B",
            "motif": "Test",
            "date_absence": "2026-06-15",
        }
        response = self.client.post(
            reverse("api_absences"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_psp_post_team_member_allowed(self):
        payload = {
            "equipe": "Berceau",
            "effectif": self.team_op.id,
            "remplacant_effectif": self.replacement.id,
            "shift": "A",
            "motif": "Formation",
            "remplacant": "",
            "date_absence": "2026-06-20",
        }
        response = self.client.post(
            reverse("api_absences"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_psp_delete_forbidden(self):
        response = self.client.delete(
            reverse("api_absence_detail", kwargs={"pk": self.absence_team.id}),
        )
        self.assertEqual(response.status_code, 403)


class ModeDegradeApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username="modedegradeadmin", password="strong-pass-123")
        self.client.login(username="modedegradeadmin", password="strong-pass-123")

    def _payload(self):
        return {
            "equipe": "Berceau",
            "shift": "A",
            "action": "Plan de rattrapage",
            "probleme": "Panne machine",
            "pilote": "Chef UEP",
            "date": "2026-05-02",
            "delai": "2026-05-05",
            "cause": "Capteur defectueux",
            "statut": "Ouvert",
        }

    def test_mode_degrade_api_crud(self):
        import json

        create_response = self.client.post(
            reverse("api_mode_degrade"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        created_id = create_response.json()["id"]

        list_response = self.client.get(reverse("api_mode_degrade"), {"q": "Panne"})
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(list_response.json()["total"], 1)

        detail_response = self.client.get(reverse("api_mode_degrade_detail", kwargs={"pk": created_id}))
        self.assertEqual(detail_response.status_code, 200)

        update_payload = self._payload()
        update_payload["statut"] = "En cours"
        update_response = self.client.patch(
            reverse("api_mode_degrade_detail", kwargs={"pk": created_id}),
            data=json.dumps(update_payload),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)

        delete_response = self.client.delete(reverse("api_mode_degrade_detail", kwargs={"pk": created_id}))
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(ModeDegrade.objects.filter(is_deleted=False).count(), 0)


class PspModeDegradeBerceauTests(TestCase):
    """PSP Berceau : liste filtrée par shift, pas de DELETE, POST cross-shift refusé."""

    def setUp(self):
        suffix = get_random_string(8)
        User = get_user_model()
        self.psp_effectif = OperateurEffectif.objects.create(
            nom_complet=f"PSP MD {suffix}",
            shift="A",
            cin=f"PMD{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=f"PSP-MD-{suffix}",
            num_tel="+212612303001",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        self.incident_a = ModeDegrade.objects.create(
            equipe="Berceau",
            shift="A",
            action="Action A",
            probleme="Probleme shift A",
            pilote="Pilote A",
            date=date(2026, 7, 1),
            delai=date(2026, 7, 5),
            cause="Cause A",
            statut="Ouvert",
        )
        self.incident_b = ModeDegrade.objects.create(
            equipe="Berceau",
            shift="B",
            action="Action B",
            probleme="Probleme shift B",
            pilote="Pilote B",
            date=date(2026, 7, 2),
            delai=date(2026, 7, 6),
            cause="Cause B",
            statut="Ouvert",
        )
        self.psp_user = User.objects.create_user(username=f"psp_md_{suffix}", password="strong-pass-123")
        UserAccessProfile.objects.update_or_create(
            user=self.psp_user,
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": self.psp_effectif},
        )
        self.client.login(username=self.psp_user.username, password="strong-pass-123")

    def test_psp_list_only_own_shift(self):
        response = self.client.get(reverse("api_mode_degrade"), {"equipe": "Berceau"})
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertIn(self.incident_a.id, ids)
        self.assertNotIn(self.incident_b.id, ids)

    def test_psp_post_cross_shift_forbidden(self):
        payload = {
            "equipe": "Berceau",
            "shift": "B",
            "action": "Plan",
            "probleme": "Test",
            "pilote": "PSP",
            "date": "2026-07-10",
            "delai": "2026-07-12",
            "cause": "Test",
            "statut": "Ouvert",
        }
        response = self.client.post(
            reverse("api_mode_degrade"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_psp_delete_forbidden(self):
        response = self.client.delete(
            reverse("api_mode_degrade_detail", kwargs={"pk": self.incident_a.id}),
        )
        self.assertEqual(response.status_code, 403)


class StockJournalBerceauTests(TestCase):
    """Stock Berceau A1/A3 : cohérence stock_fin, RBAC sortie montage."""

    def setUp(self):
        suffix = get_random_string(8)
        User = get_user_model()
        self.target_date = date(2026, 9, 10)
        self.prev_date = date(2026, 9, 9)

        StockJournal.objects.create(
            date=self.prev_date,
            equipe="Berceau",
            line="A1",
            stock_debut=0,
            entree_calculee=0,
            sortie_montage=0,
            stock_fin=100,
        )

        ProductionBerceau.objects.create(
            line="A1",
            date=self.target_date,
            shift="A",
            objectif=60,
            production_h1=60,
            rebut=0,
            retouche=0,
            temps_arrets_h1=0,
            temps_arrets_h2=0,
            temps_arrets_h3=0,
            temps_arrets_h4=0,
            temps_arrets_h5=0,
            temps_arrets_h6=0,
            temps_arrets_h7=0,
            temps_arrets_h8=0,
        )
        ProductionBerceau.objects.create(
            line="A1",
            date=self.target_date,
            shift="B",
            objectif=40,
            production_h1=40,
            rebut=0,
            retouche=0,
            temps_arrets_h1=0,
            temps_arrets_h2=0,
            temps_arrets_h3=0,
            temps_arrets_h4=0,
            temps_arrets_h5=0,
            temps_arrets_h6=0,
            temps_arrets_h7=0,
            temps_arrets_h8=0,
        )

        self.ru_user = User.objects.create_user(username=f"ru_stock_{suffix}", password="strong-pass-123")
        UserAccessProfile.objects.update_or_create(
            user=self.ru_user,
            defaults={"role": UserAccessProfile.Role.RU, "effectif": None},
        )

        self.psp_effectif = OperateurEffectif.objects.create(
            nom_complet=f"PSP Stock {suffix}",
            shift="A",
            cin=f"PST{suffix[:4]}",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=f"PSP-ST-{suffix}",
            num_tel="+212612303099",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        self.psp_user = User.objects.create_user(username=f"psp_stock_{suffix}", password="strong-pass-123")
        UserAccessProfile.objects.update_or_create(
            user=self.psp_user,
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": self.psp_effectif},
        )

    def test_ru_update_stock_fin_coherent(self):
        self.client.login(username=self.ru_user.username, password="strong-pass-123")
        response = self.client.post(
            reverse("api_stock_journal_update"),
            data=json.dumps(
                {
                    "equipe": "Berceau",
                    "line": "A1",
                    "date": self.target_date.isoformat(),
                    "sortie_montage": 50,
                    "note": "test",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["entree_calculee"], 100)
        self.assertEqual(body["stock_debut"], 100)
        self.assertEqual(body["sortie_montage"], 50)
        self.assertEqual(body["stock_fin"], body["stock_debut"] + body["entree_calculee"] - body["sortie_montage"])

    def test_psp_journal_shift_prorata(self):
        StockJournal.objects.create(
            date=self.target_date,
            equipe="Berceau",
            line="A1",
            stock_debut=100,
            entree_calculee=100,
            sortie_montage=50,
            stock_fin=150,
        )
        self.client.login(username=self.psp_user.username, password="strong-pass-123")
        response = self.client.get(
            reverse("api_stock_journal"),
            {"equipe": "Berceau", "line": "A1", "date": self.target_date.isoformat(), "days": 1},
        )
        self.assertEqual(response.status_code, 200)
        current = response.json()["current"]
        self.assertEqual(current["entree_calculee"], 60)
        self.assertEqual(current["sortie_imputee"], 30)
        self.assertEqual(current["stock_fin"], 100 + 60 - 30)

    def test_psp_cannot_update_sortie(self):
        self.client.login(username=self.psp_user.username, password="strong-pass-123")
        response = self.client.post(
            reverse("api_stock_journal_update"),
            data=json.dumps(
                {
                    "equipe": "Berceau",
                    "line": "A1",
                    "date": self.target_date.isoformat(),
                    "sortie_montage": 10,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class AlertePanneBerceauTests(TestCase):
    def setUp(self):
        from .models import (
            AlertePanne,
            ArretBerceau,
            BerceauModule,
            BerceauMoyen,
            BerceauPoste,
            PanneType,
            UserAccessProfile,
        )

        self.AlertePanne = AlertePanne
        self.ArretBerceau = ArretBerceau
        self.BerceauModule = BerceauModule
        self.BerceauPoste = BerceauPoste
        self.BerceauMoyen = BerceauMoyen
        self.PanneType = PanneType
        self.UserAccessProfile = UserAccessProfile

        User = get_user_model()
        suffix = get_random_string(8)
        self.user = User.objects.create_user(username=f"ru_panne_{suffix}", password="strong-pass-123")
        self.client.login(username=self.user.username, password="strong-pass-123")
        self.UserAccessProfile.objects.update_or_create(
            user=self.user,
            defaults={"role": self.UserAccessProfile.Role.RU, "effectif": None},
        )

        self.mod = self.BerceauModule.objects.create(name=f"Module T {suffix}")
        self.poste = self.BerceauPoste.objects.create(module=self.mod, name="Poste T")
        self.moyen = self.BerceauMoyen.objects.create(poste=self.poste, name="Moyen T")
        self.panne_type = self.PanneType.objects.create(name=f"Type T {suffix}")

    def test_hierarchy_validation(self):
        other_mod = self.BerceauModule.objects.create(name=f"Module X {get_random_string(4)}")
        bad_poste = self.BerceauPoste.objects.create(module=other_mod, name="Poste X")
        payload = {
            "module_id": self.mod.id,
            "poste_id": bad_poste.id,
            "moyen_id": self.moyen.id,
            "panne_type_id": self.panne_type.id,
            "category": "maintenance",
            "cause": "Cause",
            "solution": "Solution",
            "date": "2026-06-01",
            "shift": "A",
            "heure_production": 1,
            "temps_arret_min": 5,
        }
        res = self.client.post(reverse("api_alertes_pannes"), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_heure_production_range(self):
        payload = {
            "module_id": self.mod.id,
            "poste_id": self.poste.id,
            "moyen_id": self.moyen.id,
            "panne_type_id": self.panne_type.id,
            "category": "maintenance",
            "cause": "Cause",
            "solution": "Solution",
            "date": "2026-06-01",
            "shift": "A",
            "heure_production": 9,
            "temps_arret_min": 0,
        }
        res = self.client.post(reverse("api_alertes_pannes"), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_temps_auto_endpoint(self):
        self.ArretBerceau.objects.create(
            module=self.mod,
            poste=self.poste,
            moyen=self.moyen,
            date="2026-06-01",
            shift="A",
            heure_production=2,
            temps_arret_min=17,
        )
        res = self.client.get(
            reverse("api_arrets_temps_auto"),
            {
                "date": "2026-06-01",
                "shift": "A",
                "module_id": self.mod.id,
                "poste_id": self.poste.id,
                "moyen_id": self.moyen.id,
                "heure": 2,
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["temps_arret_min"], 17)
        self.assertTrue(res.json()["found"])

    def test_dynamic_dependency_endpoints_and_creation(self):
        mods = self.client.get(reverse("api_berceau_modules"))
        self.assertEqual(mods.status_code, 200)
        self.assertGreaterEqual(len(mods.json()["results"]), 1)

        postes = self.client.get(reverse("api_berceau_module_postes", kwargs={"module_id": self.mod.id}))
        self.assertEqual(postes.status_code, 200)
        self.assertTrue(any(p["id"] == self.poste.id for p in postes.json()["results"]))

        moyens = self.client.get(reverse("api_berceau_poste_moyens", kwargs={"poste_id": self.poste.id}))
        self.assertEqual(moyens.status_code, 200)
        self.assertTrue(any(m["id"] == self.moyen.id for m in moyens.json()["results"]))

        custom_name = f"Nouvelle panne {get_random_string(4)}"
        new_type = self.client.post(
            reverse("api_panne_types"),
            data=json.dumps({"name": custom_name}),
            content_type="application/json",
        )
        self.assertEqual(new_type.status_code, 201)
        listed = self.client.get(reverse("api_panne_types"), {"equipe": "Berceau"})
        self.assertEqual(listed.status_code, 200)
        listed_names = [row["name"] for row in listed.json()["results"]]
        self.assertIn(custom_name, listed_names)
        type_id = new_type.json()["id"]
        renamed = self.client.patch(
            reverse("api_panne_type_detail", kwargs={"pk": type_id}) + "?equipe=Berceau",
            data=json.dumps({"name": f"{custom_name} modifie"}),
            content_type="application/json",
        )
        self.assertEqual(renamed.status_code, 200)
        payload = {
            "module_id": self.mod.id,
            "poste_id": self.poste.id,
            "moyen_id": self.moyen.id,
            "panne_type_id": type_id,
            "category": "logistique",
            "cause": "Cause test",
            "solution": "Solution test",
            "date": "2026-06-01",
            "shift": "A",
            "heure_production": 1,
            "temps_arret_min": 5,
        }
        created = self.client.post(
            reverse("api_alertes_pannes"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(created.status_code, 201)

    def test_panne_type_delete_after_soft_deleted_alerte_deactivates(self):
        """Suppression d'un type encore référencé par un arrêt archivé (is_deleted) : désactivation, pas 500."""
        custom_name = f"Type del {get_random_string(4)}"
        new_type = self.client.post(
            reverse("api_panne_types"),
            data=json.dumps({"name": custom_name}),
            content_type="application/json",
        )
        self.assertEqual(new_type.status_code, 201)
        type_id = new_type.json()["id"]
        payload = {
            "module_id": self.mod.id,
            "poste_id": self.poste.id,
            "moyen_id": self.moyen.id,
            "panne_type_id": type_id,
            "category": "logistique",
            "cause": "Cause test",
            "solution": "Solution test",
            "date": "2026-06-01",
            "shift": "A",
            "heure_production": 1,
            "temps_arret_min": 5,
        }
        created = self.client.post(
            reverse("api_alertes_pannes"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(created.status_code, 201)
        alerte_id = created.json()["id"]
        del_alerte = self.client.delete(reverse("api_alertes_pannes_detail", kwargs={"pk": alerte_id}))
        self.assertEqual(del_alerte.status_code, 200)

        del_type = self.client.delete(
            reverse("api_panne_type_detail", kwargs={"pk": type_id}) + "?equipe=Berceau"
        )
        self.assertEqual(del_type.status_code, 200)
        self.assertTrue(del_type.json().get("deactivated"))

        listed = self.client.get(reverse("api_panne_types"), {"equipe": "Berceau"})
        self.assertEqual(listed.status_code, 200)
        self.assertNotIn(custom_name, [row["name"] for row in listed.json()["results"]])
        self.PanneType.objects.get(pk=type_id, is_active=False)

    def test_panne_type_delete_unused_custom_type_hard_removed(self):
        custom_name = f"Type orphan {get_random_string(4)}"
        new_type = self.client.post(
            reverse("api_panne_types"),
            data=json.dumps({"name": custom_name}),
            content_type="application/json",
        )
        self.assertEqual(new_type.status_code, 201)
        type_id = new_type.json()["id"]
        del_type = self.client.delete(
            reverse("api_panne_type_detail", kwargs={"pk": type_id}) + "?equipe=Berceau"
        )
        self.assertEqual(del_type.status_code, 200)
        self.assertTrue(del_type.json().get("removed"))
        self.assertFalse(self.PanneType.objects.filter(pk=type_id).exists())

    def test_multiple_alertes_same_day_hour_are_all_saved(self):
        payload = {
            "module_id": self.mod.id,
            "poste_id": self.poste.id,
            "moyen_id": self.moyen.id,
            "panne_type_id": self.panne_type.id,
            "category": "kta",
            "cause": "Cause 1",
            "solution": "Solution 1",
            "date": "2026-06-02",
            "shift": "A",
            "heure_production": 3,
            "temps_arret_min": 2,
        }
        created1 = self.client.post(
            reverse("api_alertes_pannes"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(created1.status_code, 201)

        payload2 = {**payload, "cause": "Cause 2", "solution": "Solution 2", "category": "fabrication"}
        created2 = self.client.post(
            reverse("api_alertes_pannes"), data=json.dumps(payload2), content_type="application/json"
        )
        self.assertEqual(created2.status_code, 201)

        list_res = self.client.get(reverse("api_alertes_pannes"), {"date": "2026-06-02", "shift": "A"})
        self.assertEqual(list_res.status_code, 200)
        rows = [r for r in list_res.json()["results"] if r["heure_production"] == 3]
        self.assertGreaterEqual(len(rows), 2)


class BerceauMatrixSeedTests(TestCase):
    def test_seed_matrix_contains_expected_structure(self):
        from django.core.management import call_command

        from .models import BerceauModule, BerceauMoyen, BerceauPoste

        call_command("seed_berceau_matrix")

        self.assertTrue(BerceauModule.objects.filter(name="OP05").exists())
        self.assertTrue(BerceauModule.objects.filter(name="Module 1").exists())
        self.assertTrue(BerceauModule.objects.filter(name="Module 2").exists())

        op100 = BerceauPoste.objects.get(module__name="Module 2", name="OP100")
        self.assertFalse(op100.a1_enabled)
        self.assertTrue(op100.a3_enabled)

        # Dedup rule applied on OP90 moyens list (R20 duplicated in source but stored once per poste)
        op90 = BerceauPoste.objects.get(module__name="Module 2", name="OP90")
        op90_moyens = list(BerceauMoyen.objects.filter(poste=op90).values_list("name", flat=True))
        self.assertEqual(op90_moyens.count("R20"), 1)


def _minimal_berceau_json_payload(shift="A", line="A1", dt="2026-06-15"):
    """Minimal valid JSON body for POST /api/berceau/production/."""
    oh = {f"objectif_h{i}": 0 for i in range(1, 9)}
    lh = {f"line_h{i}": line for i in range(1, 9)}
    ph = {f"production_h{i}": (55 if i == 1 else 0) for i in range(1, 9)}
    rh = {f"rebut_h{i}": 0 for i in range(1, 9)}
    rth = {f"retouche_h{i}": 0 for i in range(1, 9)}
    ta = {f"temps_arrets_h{i}": 0 for i in range(1, 9)}
    return {
        "line": line,
        "date": dt,
        "shift": shift,
        "objectif": 100,
        **oh,
        **lh,
        **ph,
        **rh,
        **rth,
        **ta,
        "rebut": 0,
        "retouche": 0,
        "temps_arrets": 0,
    }


class ProductionBerceauHourlyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username="hourlyadmin", password="strong-pass-123")
        self.client.login(username="hourlyadmin", password="strong-pass-123")

    def test_model_totals_and_nro_are_backend_computed(self):
        payload = _minimal_berceau_json_payload(shift="A", line="A1", dt="2026-09-01")
        payload.update({"rebut_h1": 2, "retouche_h1": 3, "temps_arrets_h1": 5})
        response = self.client.post(
            reverse("api_production_berceau"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        row = response.json()
        self.assertEqual(row["volume"], 55)
        self.assertEqual(row["rebut"], 2)
        self.assertEqual(row["retouche"], 3)
        # arrets are computed from ArretBerceau module, not from production payload
        self.assertEqual(row["temps_arrets"], 0)
        self.assertEqual(row["nro_total"], 45)

    def test_hourly_arrets_are_aggregated_from_arret_module(self):
        from .models import ArretBerceau, BerceauModule, BerceauMoyen, BerceauPoste

        mod = BerceauModule.objects.create(name=f"MOD-{get_random_string(5)}")
        poste = BerceauPoste.objects.create(module=mod, name=f"POSTE-{get_random_string(5)}")
        moyen = BerceauMoyen.objects.create(poste=poste, name=f"MOYEN-{get_random_string(5)}")
        ArretBerceau.objects.create(
            module=mod,
            poste=poste,
            moyen=moyen,
            date="2026-09-04",
            shift="A",
            heure_production=1,
            temps_arret_min=5,
        )
        ArretBerceau.objects.create(
            module=mod,
            poste=poste,
            moyen=moyen,
            date="2026-09-04",
            shift="A",
            heure_production=2,
            temps_arret_min=7,
        )

        payload = _minimal_berceau_json_payload(shift="A", line="A1", dt="2026-09-04")
        payload.update({"temps_arrets_h1": 99, "temps_arrets_h2": 99})
        response = self.client.post(
            reverse("api_production_berceau"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        row = response.json()
        self.assertEqual(row["temps_arrets_h1"], 5)
        self.assertEqual(row["temps_arrets_h2"], 7)
        self.assertEqual(row["temps_arrets"], 12)

    def test_validate_hour_requires_sequence(self):
        payload = _minimal_berceau_json_payload(shift="A", line="A3", dt="2026-09-02")
        created = self.client.post(
            reverse("api_production_berceau"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        pk = created.json()["id"]
        bad = self.client.post(
            reverse("api_production_berceau_validate_hour", kwargs={"pk": pk}),
            data=json.dumps({"hour": 2}),
            content_type="application/json",
        )
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(
            reverse("api_production_berceau_validate_hour", kwargs={"pk": pk}),
            data=json.dumps({"hour": 1}),
            content_type="application/json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertIn(1, ok.json()["validated_hours"])

    def test_psp_can_patch_production_after_hour_validated(self):
        """Hourly validation lock is off; PSP can still PATCH production fields."""
        suffix = get_random_string(8)
        effectif = OperateurEffectif.objects.create(
            nom_complet="PSP Hourly",
            shift="A",
            cin=f"HP{suffix}",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=f"PSP-H-{suffix}",
            num_tel="+212612399999",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        User = get_user_model()
        psp = User.objects.create_user(username=f"psp_hour_{suffix}", password="strong-pass-123")
        UserAccessProfile.objects.update_or_create(
            user=psp,
            defaults={"role": UserAccessProfile.Role.PSP, "effectif": effectif},
        )
        self.client.logout()
        self.client.login(username=psp.username, password="strong-pass-123")
        payload = _minimal_berceau_json_payload(shift="A", line="A1", dt="2026-09-03")
        created = self.client.post(
            reverse("api_production_berceau"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        pk = created.json()["id"]
        v = self.client.post(
            reverse("api_production_berceau_validate_hour", kwargs={"pk": pk}),
            data=json.dumps({"hour": 1}),
            content_type="application/json",
        )
        self.assertEqual(v.status_code, 200)
        detail = self.client.get(reverse("api_production_berceau_detail", kwargs={"pk": pk}))
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        for k in ("ro_percent", "nro_total", "validated_hours", "arrets_source", "id"):
            body.pop(k, None)
        body["production_h1"] = 99
        patch = self.client.patch(
            reverse("api_production_berceau_detail", kwargs={"pk": pk}),
            data=json.dumps(body),
            content_type="application/json",
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(patch.json()["production_h1"], 99)


class AuthApiTests(TestCase):
    """Session JSON auth: identifiant + code."""

    def test_auth_me_anonymous_returns_401(self):
        response = self.client.get(reverse("api_auth_me"))
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json().get("authenticated"))

    def test_auth_login_invalid_returns_401(self):
        response = self.client.post(
            reverse("api_auth_login"),
            data=json.dumps({"identifiant": "nope", "code": "bad-password"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_auth_login_me_logout_roundtrip(self):
        User = get_user_model()
        suffix = get_random_string(8)
        user = User.objects.create_user(username=f"juser_{suffix}", password="strong-pass-123")
        login_r = self.client.post(
            reverse("api_auth_login"),
            data=json.dumps({"identifiant": user.username, "code": "strong-pass-123"}),
            content_type="application/json",
        )
        self.assertEqual(login_r.status_code, 200)
        body = login_r.json()
        self.assertTrue(body["authenticated"])
        self.assertEqual(body["role"], UserAccessProfile.Role.RU)

        me = self.client.get(reverse("api_auth_me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["identifiant"], user.username)

        self.client.post(reverse("api_auth_logout"))
        again = self.client.get(reverse("api_auth_me"))
        self.assertEqual(again.status_code, 401)

    def test_auth_login_psp_me_resolves_equipe_via_identifiant_when_profile_effectif_unset(self):
        """PSP scope when UserAccessProfile.effectif is empty but login identifiant matches Effectif.identifiant."""
        User = get_user_model()
        suffix = get_random_string(8)
        ident = f"psp_fb_{suffix}"
        user = User.objects.create_user(username=ident, password="strong-pass-123")
        UserAccessProfile.objects.create(
            user=user,
            role=UserAccessProfile.Role.PSP,
            effectif=None,
        )
        eff = OperateurEffectif.objects.create(
            nom_complet="PSP Fallback Scope",
            shift="N",
            cin=f"CINFB{suffix}",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=ident,
            num_tel="+212612300099",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="CCB",
        )
        login_r = self.client.post(
            reverse("api_auth_login"),
            data=json.dumps({"identifiant": ident, "code": "strong-pass-123"}),
            content_type="application/json",
        )
        self.assertEqual(login_r.status_code, 200)
        body = login_r.json()
        self.assertEqual(body["role"], UserAccessProfile.Role.PSP)
        self.assertEqual(body["equipe"], "CCB")
        self.assertEqual(body["shift"], "N")
        self.assertEqual(body["effectif_id"], eff.id)

    def test_auth_login_psp_me_resolves_via_seed_username_br_psp_a_pattern(self):
        """Login username br_psp_a resolves Berceau shift A PSP row even if identifiant is MAT-BR-PSP-A."""
        User = get_user_model()
        user = User.objects.create_user(username="br_psp_a", password="seed-pattern-test-9")
        UserAccessProfile.objects.create(
            user=user,
            role=UserAccessProfile.Role.PSP,
            effectif=None,
        )
        eff = OperateurEffectif.objects.create(
            nom_complet="PSP Seed Pattern",
            shift="A",
            cin="BRSEEDPATA",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant="MAT-BR-PSP-A",
            num_tel="+212612300088",
            sexe="Homme",
            fonction="PSP",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Pilotage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        login_r = self.client.post(
            reverse("api_auth_login"),
            data=json.dumps({"identifiant": "br_psp_a", "code": "seed-pattern-test-9"}),
            content_type="application/json",
        )
        self.assertEqual(login_r.status_code, 200)
        body = login_r.json()
        self.assertEqual(body["equipe"], "Berceau")
        self.assertEqual(body["shift"], "A")
        self.assertEqual(body["effectif_id"], eff.id)


class PspProductionBerceauTests(TestCase):
    """RBAC PSP: liste filtree par shift (Effectif); POST cross-shift refuse; shift dynamique."""

    def setUp(self):
        suffix = get_random_string(8)
        self.effectif = OperateurEffectif.objects.create(
            nom_complet="PSP Operator",
            shift="A",
            cin=f"P{suffix}01",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=f"EMP-PSP-{suffix}",
            num_tel="+212612300001",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="C1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Sale",
            equipe="Berceau",
        )
        User = get_user_model()
        self.psp_user = User.objects.create_user(username=f"psp_{suffix}", password="strong-pass-123")
        UserAccessProfile.objects.update_or_create(
            user=self.psp_user,
            defaults={
                "role": UserAccessProfile.Role.PSP,
                "effectif": self.effectif,
            },
        )

        self.day_a = date(2026, 8, 1)
        self.day_b = date(2026, 8, 2)
        self.prod_shift_a = ProductionBerceau.objects.create(
            line="A1",
            date=self.day_a,
            shift="A",
            objectif=50,
            production_h1=50,
            rebut=0,
            retouche=0,
            temps_arrets_h1=0,
            temps_arrets_h2=0,
            temps_arrets_h3=0,
            temps_arrets_h4=0,
            temps_arrets_h5=0,
            temps_arrets_h6=0,
            temps_arrets_h7=0,
            temps_arrets_h8=0,
        )
        self.prod_shift_b = ProductionBerceau.objects.create(
            line="A3",
            date=self.day_b,
            shift="B",
            objectif=40,
            production_h1=40,
            rebut=0,
            retouche=0,
            temps_arrets_h1=0,
            temps_arrets_h2=0,
            temps_arrets_h3=0,
            temps_arrets_h4=0,
            temps_arrets_h5=0,
            temps_arrets_h6=0,
            temps_arrets_h7=0,
            temps_arrets_h8=0,
        )

        self.client.login(username=self.psp_user.username, password="strong-pass-123")

    def test_psp_list_only_own_shift(self):
        response = self.client.get(reverse("api_production_berceau"))
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertIn(self.prod_shift_a.id, ids)
        self.assertNotIn(self.prod_shift_b.id, ids)

    def test_psp_post_cross_shift_forbidden(self):
        payload = _minimal_berceau_json_payload(shift="B", line="A1", dt="2026-08-05")
        response = self.client.post(
            reverse("api_production_berceau"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_psp_shift_follows_effectif_change(self):
        self.effectif.shift = "B"
        self.effectif.save(update_fields=["shift"])

        response = self.client.get(reverse("api_production_berceau"))
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertNotIn(self.prod_shift_a.id, ids)
        self.assertIn(self.prod_shift_b.id, ids)

    def test_psp_delete_forbidden(self):
        response = self.client.delete(
            reverse("api_production_berceau_detail", kwargs={"pk": self.prod_shift_a.id}),
        )
        self.assertEqual(response.status_code, 403)


class DashboardAnalyticsTests(TestCase):
    def setUp(self):
        suffix = get_random_string(6)
        User = get_user_model()
        self.ru = User.objects.create_user(username=f"ru_dash_{suffix}", password="strong-pass-123")
        UserAccessProfile.objects.create(user=self.ru, role=UserAccessProfile.Role.RU)

        self.psp = User.objects.create_user(username=f"psp_dash_{suffix}", password="strong-pass-123")
        eff = OperateurEffectif.objects.create(
            nom_complet="PSP Dashboard",
            shift="A",
            cin=f"DASH{suffix}",
            type_contrat="CDI",
            date_naissance="1990-01-01",
            date_entree="2010-01-01",
            identifiant=f"DASH-EMP-{suffix}",
            num_tel="+212612399999",
            sexe="Homme",
            fonction="Operateur",
            ville_actuelle="Kenitra",
            niveau_etude="Bac",
            numero_casier="A1",
            parada_transport="P1",
            pointure_chaussure=42,
            specialite="Assemblage",
            taille_pantalon="M",
            taille_veste="L",
            ville_origine="Rabat",
            equipe="Berceau",
        )
        UserAccessProfile.objects.create(user=self.psp, role=UserAccessProfile.Role.PSP, effectif=eff)

        ProductionBerceau.objects.create(
            line="A1",
            date="2026-06-10",
            shift="A",
            objectif=100,
            objectif_h1=100,
            line_h1="A1",
            production_h1=80,
            rebut_h1=2,
            retouche_h1=1,
            volume=80,
            rebut=2,
            retouche=1,
            temps_arrets=0,
        )
        ProductionBerceau.objects.create(
            line="A1",
            date="2026-06-10",
            shift="B",
            objectif=100,
            objectif_h1=100,
            line_h1="A1",
            production_h1=70,
            rebut_h1=3,
            retouche_h1=1,
            volume=70,
            rebut=3,
            retouche=1,
            temps_arrets=0,
        )

    def test_ru_can_read_dashboard_all_shifts(self):
        self.client.login(username=self.ru.username, password="strong-pass-123")
        response = self.client.get(reverse("api_dashboard_ro_nro_trend"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("labels", body)
        self.assertIn("ro_percent", body["series"])
        self.assertIn("nro_percent", body["series"])

    def test_psp_dashboard_shift_restrictions(self):
        self.client.login(username=self.psp.username, password="strong-pass-123")
        forbidden = self.client.get(reverse("api_dashboard_ro_nro_trend"), {"shift": "B"})
        self.assertEqual(forbidden.status_code, 403)

        allowed = self.client.get(reverse("api_dashboard_ro_nro_trend"))
        self.assertEqual(allowed.status_code, 200)

    def test_pareto_endpoint_returns_series(self):
        self.client.login(username=self.ru.username, password="strong-pass-123")
        response = self.client.get(reverse("api_dashboard_pareto_postes"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("labels", body)
        self.assertIn("arrets_minutes", body["series"])
        self.assertIn("cumulative_percent", body["series"])

    def test_pareto_endpoint_supports_panne_type_grouping_and_poste_filter(self):
        self.client.login(username=self.ru.username, password="strong-pass-123")
        response = self.client.get(
            reverse("api_dashboard_pareto_postes"),
            {"group_by": "panne_type"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("meta", body)
        self.assertEqual(body["meta"]["group_by"], "panne_type")


class DowntimeImpactTests(TestCase):
    """Pure logic for Berceau downtime → production impact % (Pareto)."""

    def test_downtime_impact_percent_a1(self):
        # (13 / 1.3) * (100 / 100) = 10
        self.assertAlmostEqual(downtime_impact_percent(13, "A1", 100), 10.0, places=6)

    def test_downtime_impact_percent_a3(self):
        # (18 / 1.8) * (100 / 100) = 10
        self.assertAlmostEqual(downtime_impact_percent(18, "A3", 100), 10.0, places=6)

    def test_downtime_impact_percent_zero_or_missing_inputs(self):
        self.assertEqual(downtime_impact_percent(10, "A1", 0), 0.0)
        self.assertEqual(downtime_impact_percent(10, None, 100), 0.0)
        self.assertEqual(downtime_impact_percent(0, "A1", 100), 0.0)

    def test_parse_diversite_from_cause(self):
        self.assertEqual(parse_diversite_from_cause("[diversite:A3] Panne"), "A3")
        self.assertIsNone(parse_diversite_from_cause("sans tag"))

    def test_hourly_objective_prefers_row_matching_diversity(self):
        low = SimpleNamespace(objectif_h2=40, line_h2="A3")
        high = SimpleNamespace(objectif_h2=120, line_h2="A1")
        self.assertEqual(hourly_objective_for_diversity([low, high], 2, "A1"), 120)

    def test_total_objectif_for_diversity_sums_matching_hours(self):
        row = SimpleNamespace(
            line_h1="A1",
            objectif_h1=30,
            line_h2="A1",
            objectif_h2=70,
            line_h3="A3",
            objectif_h3=99,
        )
        self.assertEqual(total_objectif_for_diversity([row], "A1"), 100)
        self.assertEqual(total_objectif_for_diversity([row], "A3"), 99)

    def test_berceau_alerte_impact_uses_shift_objectif_sum_hours_not_single_hour_only(self):
        alerte = SimpleNamespace(cause="plain", heure_production=1, temps_arret_min=13)
        prod = SimpleNamespace(line_h1="A1", objectif_h1=30, line_h2="A1", objectif_h2=70)
        self.assertAlmostEqual(berceau_alerte_impact_pct(alerte, [prod]), 10.0, places=6)

    def test_resolve_diversity_from_production_rows(self):
        row = SimpleNamespace(line_h4="A3")
        self.assertEqual(resolve_diversity_for_impact("plain cause", [row], 4), "A3")

    def test_berceau_alerte_impact_pct_uses_explicit_tag_with_shift_objectif_denominator(self):
        alerte = SimpleNamespace(
            cause="[diversite:A1] test",
            heure_production=5,
            temps_arret_min=13,
        )
        prod = SimpleNamespace(objectif_h5=100, line_h5="A1")
        self.assertAlmostEqual(berceau_alerte_impact_pct(alerte, [prod]), 10.0, places=6)

    def test_berceau_alerte_impact_uses_shift_total_all_hours_even_when_tagged_diversity_has_no_line(self):
        """Dénominateur = Σ objectif H1–H8 ; tag A3 sans ligne A3 sur la fiche : même somme shift."""
        alerte = SimpleNamespace(
            cause="[diversite:A3] comment",
            heure_production=2,
            temps_arret_min=18,
        )
        prod = SimpleNamespace(
            line_h1="A1",
            objectif_h1=50,
            line_h2="A1",
            objectif_h2=50,
            line_h3="A1",
            objectif_h3=0,
            line_h4="A1",
            objectif_h4=0,
            line_h5="A1",
            objectif_h5=0,
            line_h6="A1",
            objectif_h6=0,
            line_h7="A1",
            objectif_h7=0,
            line_h8="A1",
            objectif_h8=0,
        )
        # (18 / 1.8) * (100 / 100) = 10
        self.assertAlmostEqual(berceau_alerte_impact_pct(alerte, [prod]), 10.0, places=6)

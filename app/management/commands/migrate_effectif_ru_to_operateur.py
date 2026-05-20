"""One-shot : anciennes lignes effectif avec fonction=RU -> OPERATEUR (champ supprimé des choix)."""

from django.core.management.base import BaseCommand

from app.models import OperateurEffectif


class Command(BaseCommand):
    help = "Met a jour en base les effectifs encore en fonction RU vers OPERATEUR. --apply pour ecrire."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Appliquer la mise a jour (defaut : compte seulement).",
        )

    def handle(self, *args, **options):
        qs = OperateurEffectif.objects.filter(fonction="RU", is_deleted=False)
        n = qs.count()
        if not options["apply"]:
            self.stdout.write(self.style.WARNING(f"Dry-run: {n} ligne(s) effectif avec fonction=RU (reexecuter avec --apply)."))
            return
        updated = qs.update(fonction="OPERATEUR")
        self.stdout.write(self.style.SUCCESS(f"Mis a jour: {updated} effectif(s) RU -> OPERATEUR."))

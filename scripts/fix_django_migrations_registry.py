"""
Remove orphaned migration rows if a broken local migrate was applied earlier.

Run from project root:
  python scripts/fix_django_migrations_registry.py

Safe to run multiple times (no-op if rows are absent).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402


def main() -> None:
    targets = [
        ("app", "0026_prune_relocated_models_state"),
        ("production_ccb", "0004_initial"),
    ]
    with connection.cursor() as cursor:
        for app, name in targets:
            cursor.execute(
                "DELETE FROM django_migrations WHERE app = %s AND name = %s",
                [app, name],
            )
            if cursor.rowcount:
                print(f"Removed django_migrations row: {app} / {name}")
    print("Done.")


if __name__ == "__main__":
    main()

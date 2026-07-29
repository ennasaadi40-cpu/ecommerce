import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from store.models import Product, Collection


class Command(BaseCommand):
    """
    Finds products that exist in the live database but are NOT listed in
    store/data/catalog.csv (i.e. anything added by hand from the admin,
    or leftover from an old import) and removes them.

    SAFE BY DEFAULT: without --apply, this only PRINTS what it would delete.
    Nothing is removed until you re-run it with --apply.

        python manage.py prune_catalog            # preview only (safe)
        python manage.py prune_catalog --apply     # actually deletes

    After deleting products, it also removes any model/category Collection
    that is left completely empty as a result (no products, no sub-models).
    """
    help = "Preview/delete products whose SKU is not in store/data/catalog.csv."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually delete. Without this flag, only a preview is printed.",
        )

    def handle(self, *args, **options):
        csv_path = Path(__file__).resolve().parents[2] / "data" / "catalog.csv"
        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f"Catalog file not found: {csv_path}"))
            return

        with open(csv_path, newline="", encoding="utf-8") as f:
            catalog_skus = {row["sku"].strip() for row in csv.DictReader(f)}

        extra_products = Product.objects.exclude(sku__in=catalog_skus).order_by(
            "collection__brand__name", "collection__name", "name"
        )
        count = extra_products.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS(
                "Nothing to prune — every product in the database matches catalog.csv."
            ))
            return

        self.stdout.write(self.style.WARNING(
            f"Found {count} product(s) NOT present in catalog.csv:"
        ))
        for p in extra_products:
            brand = p.collection.brand.name if p.collection else "?"
            model = p.collection.name if p.collection else "?"
            self.stdout.write(f"  [{p.sku}] {brand} / {model} - {p.name} (${p.price})")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING(
                "\nPREVIEW ONLY - nothing was deleted. "
                "Re-run with --apply to actually delete these."
            ))
            return

        deleted_count, _ = extra_products.delete()

        removed_collections = 0
        changed = True
        while changed:
            changed = False
            for c in Collection.objects.all():
                if not c.products.exists() and not c.children.exists() and c.parent_id is not None:
                    c.delete()
                    removed_collections += 1
                    changed = True

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {count} product(s) and {removed_collections} now-empty collection(s)."
        ))

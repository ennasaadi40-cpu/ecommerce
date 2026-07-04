import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from store.models import Brand, Collection, Product

DEFAULT_STOCK = 10


class Command(BaseCommand):
    help = "Import brands, models and products from store/data/catalog.csv (idempotent)."

    def handle(self, *args, **options):
        csv_path = Path(__file__).resolve().parents[2] / "data" / "catalog.csv"
        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f"Catalog file not found: {csv_path}"))
            return

        brands = {}
        categories = {}   # (brand_id, name) -> Collection
        models = {}       # (brand_id, category_id, name) -> Collection
        created_p = updated_p = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                bname = row["brand"].strip()
                cat_name = row["category"].strip()
                model_name = row["model"].strip()
                ptype = row["part_type"].strip()
                pname = row["product_name"].strip()
                sku = row["sku"].strip()
                try:
                    price = float(row["price"])
                except (TypeError, ValueError):
                    continue

                # Brand
                if bname not in brands:
                    brands[bname], _ = Brand.objects.get_or_create(name=bname)
                brand = brands[bname]

                # Category (top-level collection, no parent)
                ckey = (brand.id, cat_name)
                if ckey not in categories:
                    categories[ckey], _ = Collection.objects.get_or_create(
                        brand=brand, name=cat_name, parent=None
                    )
                category = categories[ckey]

                # Model (child collection under the category)
                mkey = (brand.id, category.id, model_name)
                if mkey not in models:
                    models[mkey], _ = Collection.objects.get_or_create(
                        brand=brand, name=model_name, parent=category
                    )
                model = models[mkey]

                # Product (unique by SKU); update price/name if it changed
                obj, created = Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "collection": model,
                        "name": pname,
                        "part_type": ptype,
                        "price": price,
                        "stock": DEFAULT_STOCK,
                        "is_active": True,
                    },
                )
                if created:
                    created_p += 1
                else:
                    changed = False
                    if obj.price != price:
                        obj.price = price; changed = True
                    if obj.collection_id != model.id:
                        obj.collection = model; changed = True
                    if changed:
                        obj.save(); updated_p += 1

        self.stdout.write(self.style.SUCCESS(
            f"Catalog import done: {created_p} created, {updated_p} updated, "
            f"{len(models)} models, {len(brands)} brands."
        ))
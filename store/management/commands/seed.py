"""
OPTIONAL helper: build only the brand -> series -> model category tree.

These are real device-model names (a neutral taxonomy) and NO products,
prices, SKUs or stock are created. The store stays empty of any fabricated
data — you add your real products under whichever categories you actually
stock, straight from the admin panel.

Run with:        python manage.py seed
Remove the tree: python manage.py seed --flush   (then it rebuilds empty)
Skip it entirely and create your own brands/categories in the admin instead.
"""
from django.core.management.base import BaseCommand
from store.models import Brand, Collection


# Brand -> { Series : [models...] }   (real device names only, no products)
CATALOG = {
    "Apple": {
        "iPhone": [
            "iPhone 17 Pro Max", "iPhone 17 Pro", "iPhone 17", "iPhone 16 Pro Max",
            "iPhone 16 Pro", "iPhone 16", "iPhone 15 Pro Max", "iPhone 15",
            "iPhone 14 Pro Max", "iPhone 13", "iPhone 12", "iPhone 11",
        ],
        "iPad": ["iPad Pro 12.9'", "iPad Air 5", "iPad 10", "iPad Mini 6"],
    },
    "Samsung": {
        "S Series": [
            "Galaxy S26 Ultra", "Galaxy S25 Ultra", "Galaxy S24 Ultra",
            "Galaxy S24", "Galaxy S23", "Galaxy S22",
        ],
        "A Series": ["A56 5G", "A55 5G", "A36 5G", "A15 5G", "A14"],
        "Note Series": ["Note 20 Ultra", "Note 10 Plus", "Note 9"],
    },
    "Motorola": {
        "Moto G Series": ["G 5G 2025 (XT2513)", "G Power 2025 (XT2515)", "G Play 2024 (XT2413)"],
        "Moto E Series": ["Moto E 2024", "Moto E 2023"],
    },
    "Google": {
        "Pixel": ["Pixel 10 Pro", "Pixel 9 Pro", "Pixel 9", "Pixel 8 Pro", "Pixel 8", "Pixel 7"],
    },
    "Other Brands": {
        "OnePlus": ["OnePlus 12", "OnePlus 11"],
    },
    "Accessories": {
        "Accessories": ["Cases", "Screen Protectors", "Chargers", "Tools"],
    },
}


class Command(BaseCommand):
    help = "Create the (empty) brand/series/model category tree. No products are created."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing brands/collections first")

    def handle(self, *args, **options):
        if options["flush"]:
            Collection.objects.all().delete()
            Brand.objects.all().delete()
            self.stdout.write(self.style.WARNING("Existing categories cleared."))

        for b_order, (brand_name, series_map) in enumerate(CATALOG.items()):
            brand, _ = Brand.objects.get_or_create(name=brand_name, defaults={"order": b_order})

            for s_order, (series_name, models) in enumerate(series_map.items()):
                series, _ = Collection.objects.get_or_create(
                    brand=brand, name=series_name, parent=None,
                    defaults={"order": s_order},
                )
                for m_order, model_name in enumerate(models):
                    Collection.objects.get_or_create(
                        brand=brand, name=model_name, parent=series,
                        defaults={"order": m_order},
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Created {Brand.objects.count()} brands and "
            f"{Collection.objects.count()} categories - 0 products. "
            "Add your real products from the admin panel."
        ))

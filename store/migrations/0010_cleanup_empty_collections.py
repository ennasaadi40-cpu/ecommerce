"""
Remove leftover empty placeholder collections (models with 0 products and
categories left with no children), but ONLY for brands that already have
real products (Apple, Samsung). Placeholder trees for brands with no
products yet (e.g. Motorola, Google, Accessories) are left untouched so
the owner can still add products under them later.
"""
from django.db import migrations


def cleanup(apps, schema_editor):
    Collection = apps.get_model("store", "Collection")
    Product = apps.get_model("store", "Product")

    brand_ids = set(
        Product.objects.values_list("collection__brand_id", flat=True).distinct()
    )

    changed = True
    while changed:
        changed = False
        empties = Collection.objects.filter(
            brand_id__in=brand_ids,
            children__isnull=True,
            products__isnull=True,
        )
        n = empties.count()
        if n:
            empties.delete()
            changed = True


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0009_order_models_asc"),
    ]

    operations = [
        migrations.RunPython(cleanup, noop),
    ]

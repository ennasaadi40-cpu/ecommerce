"""
Repair migration: merge duplicate model-level collections.

Migration 0006 imported the catalog and matched each model by
(brand, name, parent). On databases where the seed tree already existed
(e.g. Samsung -> "S Series" -> "Galaxy S25 Ultra"), the CSV used a
different parent category ("Galaxy"), so duplicate model collections were
created and the products were attached to the new copies -- leaving the
old (menu-linked) copies empty: "No parts added here yet."

This migration merges every group of collections that share the same
(brand, name) at model level (parent is not NULL):
  * survivor = the copy with the most products (tie -> oldest id)
  * products and child collections of the losers are moved to the survivor
  * empty duplicate copies are deleted
Categories that end up with no children and no products are removed too.
"""
from django.db import migrations
from django.db.models import Count


def merge_duplicates(apps, schema_editor):
    Collection = apps.get_model("store", "Collection")
    Product = apps.get_model("store", "Product")

    # --- 1) merge duplicate models: same (brand, name), parent not NULL ---
    dupes = (
        Collection.objects.filter(parent__isnull=False)
        .values("brand_id", "name")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
    )
    for d in dupes:
        group = list(
            Collection.objects.filter(
                brand_id=d["brand_id"], name=d["name"], parent__isnull=False
            ).annotate(pcount=Count("products")).order_by("-pcount", "id")
        )
        survivor, losers = group[0], group[1:]
        best_slug = min((c.slug for c in group), key=len)
        for loser in losers:
            Product.objects.filter(collection=loser).update(collection=survivor)
            Collection.objects.filter(parent=loser).update(parent=survivor)
            loser.delete()
        if survivor.slug != best_slug:
            survivor.slug = best_slug
            survivor.save(update_fields=["slug"])

    # --- 2) drop categories that are now completely empty ---
    empty = Collection.objects.filter(
        parent__isnull=True, children__isnull=True, products__isnull=True
    )
    # only delete categories whose brand actually has products elsewhere,
    # so hand-made placeholder trees for future brands are left untouched
    for cat in list(empty):
        has_real_products = Product.objects.filter(
            collection__brand_id=cat.brand_id
        ).exists()
        if has_real_products:
            cat.delete()


def noop(apps, schema_editor):
    # Merging is not reversible; reversing is a no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0006_import_catalog"),
    ]

    operations = [
        migrations.RunPython(merge_duplicates, noop),
    ]

import csv
from pathlib import Path
from django.db import migrations
from django.utils.text import slugify

DEFAULT_STOCK = 10


def _unique_slug(model_cls, base, taken):
    slug = base or "item"
    candidate = slug
    n = 2
    while candidate in taken or model_cls.objects.filter(slug=candidate).exists():
        candidate = f"{slug}-{n}"
        n += 1
    taken.add(candidate)
    return candidate


def import_catalog(apps, schema_editor):
    Brand = apps.get_model("store", "Brand")
    Collection = apps.get_model("store", "Collection")
    Product = apps.get_model("store", "Product")

    csv_path = Path(__file__).resolve().parents[1] / "data" / "catalog.csv"
    if not csv_path.exists():
        return

    brand_slugs, coll_slugs, prod_slugs = set(), set(), set()
    brands, categories, models = {}, {}, {}

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

            if bname not in brands:
                b = Brand.objects.filter(name=bname).first()
                if not b:
                    b = Brand.objects.create(
                        name=bname,
                        slug=_unique_slug(Brand, slugify(bname), brand_slugs),
                        is_active=True,
                    )
                brands[bname] = b
            brand = brands[bname]

            ckey = (brand.id, cat_name)
            if ckey not in categories:
                c = Collection.objects.filter(brand=brand, name=cat_name, parent=None).first()
                if not c:
                    c = Collection.objects.create(
                        brand=brand, name=cat_name, parent=None, is_active=True,
                        slug=_unique_slug(Collection, slugify(f"{bname}-{cat_name}"), coll_slugs),
                    )
                categories[ckey] = c
            category = categories[ckey]

            mkey = (brand.id, category.id, model_name)
            if mkey not in models:
                m = Collection.objects.filter(brand=brand, name=model_name, parent=category).first()
                if not m:
                    m = Collection.objects.create(
                        brand=brand, name=model_name, parent=category, is_active=True,
                        slug=_unique_slug(Collection, slugify(f"{bname}-{model_name}"), coll_slugs),
                    )
                models[mkey] = m
            model = models[mkey]

            if not Product.objects.filter(sku=sku).exists():
                Product.objects.create(
                    collection=model, name=pname, sku=sku, part_type=ptype,
                    price=price, stock=DEFAULT_STOCK, is_active=True,
                    slug=_unique_slug(Product, slugify(f"{pname}-{sku}"), prod_slugs),
                )


def unimport_catalog(apps, schema_editor):
    # Reverse: remove products that came from the price-list import (SKU prefix XLS-).
    Product = apps.get_model("store", "Product")
    Product.objects.filter(sku__startswith="XLS-").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0005_productimage"),
    ]

    operations = [
        migrations.RunPython(import_catalog, unimport_catalog),
    ]
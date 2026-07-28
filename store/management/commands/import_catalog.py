import csv
import re
from pathlib import Path
from django.core.files import File
from django.core.management.base import BaseCommand
from store.models import Brand, Collection, Product, ProductImage

DEFAULT_STOCK = 10
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
GALLERY_SUFFIX_RE = re.compile(r"^(?P<sku>XLS-\d{4})-(?P<n>\d+)$")


def build_image_index(images_dir: Path) -> dict:
    """Map SKU -> {'primary': path, 'gallery': [paths]} by scanning
    store/data/images/** recursively.
    - store/data/images/battery/XLS-0079.jpeg       -> primary image for XLS-0079
    - store/data/images/backglass/XLS-0300-2.jpeg   -> extra gallery image for XLS-0300
    """
    index = {}
    if not images_dir.exists():
        return index
    for path in images_dir.rglob("*"):
        if not (path.is_file() and path.suffix.lower() in IMAGE_EXTS):
            continue
        stem = path.stem
        m = GALLERY_SUFFIX_RE.match(stem)
        if m:
            sku = m.group("sku")
            index.setdefault(sku, {"primary": None, "gallery": []})
            index[sku]["gallery"].append(path)
        else:
            index.setdefault(stem, {"primary": None, "gallery": []})
            index[stem]["primary"] = path
    for entry in index.values():
        entry["gallery"].sort(key=lambda p: p.name)
    return index


class Command(BaseCommand):
    help = "Import brands, models and products from store/data/catalog.csv (idempotent)."

    def handle(self, *args, **options):
        csv_path = Path(__file__).resolve().parents[2] / "data" / "catalog.csv"
        images_dir = Path(__file__).resolve().parents[2] / "data" / "images"
        image_index = build_image_index(images_dir)
        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f"Catalog file not found: {csv_path}"))
            return

        brands = {}
        categories = {}   # (brand_id, name) -> Collection
        models = {}       # (brand_id, category_id, name) -> Collection
        created_p = updated_p = images_added = gallery_added = 0

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
                    # Match by (brand, name) regardless of parent, so a model that
                    # already exists under another category (e.g. the seed tree's
                    # "S Series") is reused instead of duplicated.
                    m = Collection.objects.filter(
                        brand=brand, name=model_name, parent__isnull=False
                    ).first()
                    if not m:
                        m = Collection.objects.create(
                            brand=brand, name=model_name, parent=category
                        )
                    models[mkey] = m
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

                # Attach the primary image if we found one for this SKU.
                entry = image_index.get(sku)
                if entry and entry["primary"]:
                    img_path = entry["primary"]
                    with open(img_path, "rb") as fh:
                        obj.image.save(img_path.name, File(fh), save=True)
                    images_added += 1

                # Attach any extra gallery images (SKU-2, SKU-3, ...), skipping
                # ones already saved for this product (matched by filename).
                if entry and entry["gallery"]:
                    existing_names = set(
                        obj.images.values_list("image", flat=True)
                    )
                    for gpath in entry["gallery"]:
                        if any(gpath.name in n for n in existing_names):
                            continue
                        with open(gpath, "rb") as fh:
                            pi = ProductImage(product=obj)
                            pi.image.save(gpath.name, File(fh), save=True)
                        gallery_added += 1

        self.stdout.write(self.style.SUCCESS(
            f"Catalog import done: {created_p} created, {updated_p} updated, "
            f"{images_added} images attached, {gallery_added} gallery images added, "
            f"{len(models)} models, {len(brands)} brands."
        ))

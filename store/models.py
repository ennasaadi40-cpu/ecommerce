from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Brand(models.Model):
    """Top-level brand shown in the mega menu: Apple, Samsung, Motorola, Google..."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Sort order in the menu")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:brand", args=[self.slug])


class Collection(models.Model):
    """
    A collection = a device model or a part group (e.g. 'iPhone 16 Pro Max',
    'S Series', 'Cases'). Self-referencing FK lets us build the nested menu
    (Brand > Series > Model) like the Shopify mega menu.
    """
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="collections")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    image = models.ImageField(upload_to="collections/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.brand.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.brand.name}-{self.name}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:collection", args=[self.slug])


class Product(models.Model):
    """A single replacement part / accessory for sale."""

    class PartType(models.TextChoices):
        SCREEN = "screen", "Screen Replacement"
        BATTERY = "battery", "Battery"
        CHARGING_PORT = "charging_port", "Charging Port"
        BACK_GLASS = "back_glass", "Back Glass"
        CAMERA = "camera", "Camera"
        CASE = "case", "Case"
        PROTECTOR = "protector", "Screen Protector"
        CHARGER = "charger", "Charger"
        TOOL = "tool", "Tool"
        OTHER = "other", "Other"

    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    sku = models.CharField(max_length=64, unique=True)
    part_type = models.CharField(
        max_length=20, choices=PartType.choices, default=PartType.SCREEN
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Original price for showing a discount",
    )
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.sku}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product", args=[self.slug])

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def on_sale(self):
        return self.compare_at_price and self.compare_at_price > self.price

    @property
    def gallery(self):
        """Primary image first, then any extra images — for the product page."""
        imgs = []
        if self.image:
            imgs.append(self.image.url)
        for extra in self.images.all():
            if extra.image:
                imgs.append(extra.image.url)
        return imgs

    # ---- Color variants (e.g. "iPhone 15 Back Glass - Green") ----
    # Products whose name ends in " - <Color>" are treated as color variants
    # of the same underlying part, so listing pages can group them into one
    # card with swatches instead of repeating a near-identical card per color.

    @property
    def variant_base_name(self):
        if " - " in self.name:
            return self.name.rsplit(" - ", 1)[0].strip()
        return self.name

    @property
    def variant_color(self):
        if " - " in self.name:
            return self.name.rsplit(" - ", 1)[1].strip()
        return None

    def sibling_variants(self):
        """Other color variants of this same part (same collection, part type,
        and base name), used to render a color swatch picker."""
        if not self.variant_color:
            return Product.objects.none()
        return Product.objects.filter(
            collection_id=self.collection_id,
            part_type=self.part_type,
            is_active=True,
            name__startswith=f"{self.variant_base_name} - ",
        ).exclude(id=self.id)

    @property
    def swatch_hex(self):
        """Best-effort hex color for a small swatch dot, guessed from the
        color name. Falls back to a neutral gray if nothing matches."""
        if not self.variant_color:
            return "#cccccc"
        c = self.variant_color.lower()
        table = [
            ("rose gold", "#e8c5b5"), ("pacific blue", "#3c4d5c"),
            ("sierra blue", "#a3bcd4"), ("alpine green", "#4a5d4e"),
            ("space black", "#3b3a3e"), ("deep purple", "#54495e"),
            ("midnight", "#1e2230"), ("starlight", "#f0e6d3"),
            ("cosmic orange", "#c96a3e"), ("deep blue", "#33475b"),
            ("mist blue", "#a9c0cf"), ("natural titanium", "#8f8a80"),
            ("black titanium", "#3a3a3a"), ("white titanium", "#e8e4da"),
            ("desert titanium", "#a08a6a"), ("blue titanium", "#4c5b66"),
            ("ultramarine", "#3f4d92"), ("graphite", "#54524f"),
            ("gold", "#d4af6a"), ("silver", "#e4e4e4"),
            ("black", "#1c1c1e"), ("white", "#f5f5f0"),
            ("blue", "#3b6ea5"), ("green", "#4f6f52"),
            ("red", "#a5312f"), ("yellow", "#e0c341"),
            ("orange", "#d2691e"), ("purple", "#7a5c96"),
            ("pink", "#e8b4bc"), ("teal", "#2e7d78"),
            ("sage", "#9caf88"), ("lavender", "#b9a6d6"),
        ]
        for key, hexval in table:
            if key in c:
                return hexval
        return "#cccccc"


class ProductImage(models.Model):
    """Extra photos for a product (gallery)."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Image for {self.product.name}"


class Order(models.Model):
    """A customer order created at checkout (cart -> order)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on Delivery"
        CARD = "card", "Card"

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    note = models.TextField(blank=True)
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.full_name}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self):
        return self.price * self.quantity


class SiteConfig(models.Model):
    """
    Single editable record holding the real store information.
    Everything is blank by default — the owner fills it in from the admin,
    so the site never shows fabricated data. Templates hide any empty field.
    """
    store_name = models.CharField(max_length=120, default="RepairoX")
    announcement = models.CharField(
        max_length=200, blank=True,
        help_text="Top promo bar text. Leave empty to hide the bar.",
    )
    phone = models.CharField(max_length=40, blank=True)
    hours = models.CharField(max_length=120, blank=True, help_text="e.g. Sat–Thu: 9AM–8PM")
    email = models.EmailField(blank=True)
    notify_email = models.EmailField(
        blank=True,
        help_text="Order notifications are sent to this address. "
                  "If empty, the contact email above is used.",
    )
    address = models.CharField(max_length=255, blank=True)
    hero_title = models.CharField(max_length=150, blank=True)
    hero_subtitle = models.CharField(max_length=300, blank=True)
    about_text = models.TextField(blank=True, help_text="Shown in the footer. Leave empty to hide.")

    class Meta:
        verbose_name = "Site configuration"
        verbose_name_plural = "Site configuration"

    def __str__(self):
        return self.store_name or "Site configuration"

    @classmethod
    def get(cls):
        """Return the single config row, creating an empty one if needed."""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj
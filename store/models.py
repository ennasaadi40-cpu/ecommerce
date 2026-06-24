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
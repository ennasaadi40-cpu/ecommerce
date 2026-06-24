from decimal import Decimal
from django.conf import settings
from .models import Product


class Cart:
    """
    A simple session-based shopping cart.
    Stores {product_id: {"quantity": int, "price": str}} in request.session.
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if cart is None:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override=False):
        pid = str(product.id)
        if pid not in self.cart:
            self.cart[pid] = {"quantity": 0, "price": str(product.price)}
        if override:
            self.cart[pid]["quantity"] = quantity
        else:
            self.cart[pid]["quantity"] += quantity
        self.save()

    def remove(self, product):
        pid = str(product.id)
        if pid in self.cart:
            del self.cart[pid]
            self.save()

    def save(self):
        self.session.modified = True

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]["product"] = product
        for item in cart.values():
            item["price"] = Decimal(item["price"])
            item["subtotal"] = item["price"] * item["quantity"]
            yield item

    def __len__(self):
        return sum(item["quantity"] for item in self.cart.values())

    @property
    def total(self):
        return sum(
            Decimal(item["price"]) * item["quantity"] for item in self.cart.values()
        )

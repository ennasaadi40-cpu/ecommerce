from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Brand, Collection, Product, Order, OrderItem
from .cart import Cart
from .notifications import send_order_notification


def home(request):
    """Landing page: hero banner, featured products, services, about."""
    featured = Product.objects.filter(is_active=True)[:8]
    brands = Brand.objects.filter(is_active=True)
    return render(request, "store/home.html", {
        "featured": featured,
        "brands": brands,
    })


def brand_detail(request, slug):
    """Show ALL parts for a brand (across every model) as product cards."""
    brand = get_object_or_404(Brand, slug=slug, is_active=True)
    products = Product.objects.filter(
        collection__brand=brand, is_active=True
    ).order_by("collection__name", "name")

    paginator = Paginator(products, 12)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    # categories for the optional quick links at the top
    categories = brand.collections.filter(parent__isnull=True, is_active=True)

    return render(request, "store/brand.html", {
        "brand": brand,
        "page_obj": page_obj,
        "categories": categories,
    })


def collection_detail(request, slug):
    """List products inside a collection (a device model or part group)."""
    collection = get_object_or_404(Collection, slug=slug, is_active=True)

    # Gather products: if this is a category (has children/models), include every
    # product from all its models; if it's a leaf model, just its own products.
    child_ids = list(collection.children.filter(is_active=True).values_list("id", flat=True))
    if child_ids:
        products = Product.objects.filter(
            collection_id__in=child_ids, is_active=True
        ).order_by("collection__name", "name")
    else:
        products = collection.products.filter(is_active=True)

    paginator = Paginator(products, 12)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    return render(request, "store/collection.html", {
        "collection": collection,
        "page_obj": page_obj,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = (
        Product.objects.filter(collection=product.collection, is_active=True)
        .exclude(id=product.id)[:4]
    )
    return render(request, "store/product_detail.html", {
        "product": product,
        "related": related,
    })


def search(request):
    query = request.GET.get("q", "").strip()
    results = Product.objects.none()
    if query:
        results = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query) |
            Q(collection__name__icontains=query),
            is_active=True,
        )
    return render(request, "store/search.html", {"query": query, "results": results})


# ---------- Cart ----------

def cart_detail(request):
    return render(request, "store/cart.html", {"cart": Cart(request)})


def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get("quantity", 1))
    cart.add(product, quantity=quantity)
    messages.success(request, f"Added '{product.name}' to your cart.")
    return redirect("store:cart")


def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.info(request, "Item removed from cart.")
    return redirect("store:cart")


def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get("quantity", 1))
    if quantity > 0:
        cart.add(product, quantity=quantity, override=True)
    else:
        cart.remove(product)
    return redirect("store:cart")


# ---------- Checkout ----------

def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect("store:cart")

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "cod")
        if payment_method not in dict(Order.PaymentMethod.choices):
            payment_method = "cod"
        order = Order.objects.create(
            full_name=request.POST.get("full_name", ""),
            email=request.POST.get("email", ""),
            phone=request.POST.get("phone", ""),
            address=request.POST.get("address", ""),
            city=request.POST.get("city", ""),
            note=request.POST.get("note", ""),
            payment_method=payment_method,
        )
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                price=item["price"],
                quantity=item["quantity"],
            )
        cart.clear()
        # email the store owner about the new order (won't break checkout if it fails)
        send_order_notification(order)
        return render(request, "store/order_success.html", {"order": order})

    return render(request, "store/checkout.html", {"cart": cart})
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
    """Show all top-level collections of one brand (e.g. all Apple categories)."""
    brand = get_object_or_404(Brand, slug=slug, is_active=True)
    collections = brand.collections.filter(parent__isnull=True, is_active=True)
    return render(request, "store/brand.html", {
        "brand": brand,
        "collections": collections,
    })


def collection_detail(request, slug):
    """List products inside a collection (a device model or part group)."""
    collection = get_object_or_404(Collection, slug=slug, is_active=True)
    products = collection.products.filter(is_active=True)

    # optional filtering by part type
    part_type = request.GET.get("type")
    if part_type:
        products = products.filter(part_type=part_type)

    paginator = Paginator(products, 12)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    return render(request, "store/collection.html", {
        "collection": collection,
        "page_obj": page_obj,
        "part_types": Product.PartType.choices,
        "active_type": part_type,
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
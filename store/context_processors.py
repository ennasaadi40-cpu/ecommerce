from .models import Brand, SiteConfig
from .cart import Cart


def navigation(request):
    """
    Inject the brand menu, live cart count, and the owner-editable
    site configuration into every template.
    """
    brands = (
        Brand.objects.filter(is_active=True)
        .prefetch_related("collections__children")
    )
    return {
        "nav_brands": brands,
        "cart_count": len(Cart(request)),
        "site": SiteConfig.get(),
    }

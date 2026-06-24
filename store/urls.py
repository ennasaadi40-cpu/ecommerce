from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("brand/<slug:slug>/", views.brand_detail, name="brand"),
    path("collections/<slug:slug>/", views.collection_detail, name="collection"),
    path("product/<slug:slug>/", views.product_detail, name="product"),
    # cart
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    # checkout
    path("checkout/", views.checkout, name="checkout"),
]

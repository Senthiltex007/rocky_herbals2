from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from herbalapp import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # HOME / STATIC PAGES
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('join/', views.join, name='join'),
    path('shop-login/', views.shop_login, name='shop_login'),

    # TREE / PYRAMID VIEWS
    path('pyramid/<int:member_id>/', views.pyramid_view, name='pyramid_view'),
    path('tree/<int:member_id>/', views.tree_view, name='tree_view'),
    path('tree/modern/<str:auto_id>/', views.member_tree_modern, name='member_tree_modern'),
    path('tree/modern/', views.member_tree_modern_root, name='member_tree_modern_root'),
    path('tree/dynamic/<int:member_id>/', views.dynamic_tree, name='dynamic_tree'),
    path('tree/root/', views.member_tree_root, name='tree_root'),

    # MEMBER ROUTES
    path('members/', views.member_list, name='member_list'),
    path('members/login/', views.member_login, name='member_login'),
    path('members/register/', views.member_register, name='member_register'),
    path('member/add/<int:parent_id>/<str:position>/', views.add_member_under_parent, name='add_member'),
    path('member/delete/<int:member_id>/', views.delete_member, name='delete_member'),
    path('member/replace/<int:member_id>/', views.replace_member, name='replace_member'),
    path('member/edit/<int:member_id>/', views.edit_member, name='edit_member'),  # ✅ added

    # PRODUCT / CART / CHECKOUT
    path('products/', views.product_list, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),

    # COMMISSION / INCOME
    path('commission/credit/<int:member_id>/', views.credit_commission, name='credit_commission'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


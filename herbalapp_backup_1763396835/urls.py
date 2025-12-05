from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Admin routes
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Member routes
    path('members/add/', views.add_member, name='add_member'),
    path('members/', views.member_list, name='member_list'),
    path('members/place/', views.place_member_view, name='place_member'),
    path('members/login/', views.member_login, name='member_login'),
    path('members/register/', views.member_register, name='member_register'),
    path('member/delete/<int:member_id>/', views.delete_member, name='delete_member'),
    path('member/replace/<int:member_id>/', views.replace_member, name='replace_member'),

    # Orders, Reports, Settings
    path('orders/', views.orders, name='orders'),
    path('reports/', views.reports, name='reports'),
    path('settings/', views.settings, name='settings'),

    # Products
    path('products/', views.product_list, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),

    # ----------------------
    # MLM BINARY TREE ROUTES
    # ----------------------
    path('tree/<int:member_id>/', views.member_tree, name='member_tree'),
    path('add-member/<int:parent_id>/<str:position>/', views.add_member_under_parent, name='add_member_under_parent'),

    # Static Pages
    path('about/', views.about, name='about'),
    path('shop-login/', views.shop_login, name='shop_login'),
    path('contact/', views.contact, name='contact'),
    path('join/', views.join, name='join'),
]


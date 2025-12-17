# rocky_herbals/urls.py

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from herbalapp import views

urlpatterns = [

    # ===================== HOME / STATIC PAGES =====================
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('join/', views.join, name='join'),
    path('shop-login/', views.shop_login, name='shop_login'),

    # ===================== TREE / PYRAMID VIEWS =====================
    path('tree/root/', views.member_tree_root, name='member_tree_root'),
    path('tree/', views.member_tree_root, name='member_tree_root_default'),
    path('tree/<str:member_id>/', views.tree_view, name='tree_view'),
    path('tree/dynamic/<str:member_id>/', views.dynamic_tree, name='dynamic_tree'),
    path('tree/modern/', views.member_tree_modern_root, name='member_tree_modern_root'),
    path('tree/modern/<str:auto_id>/', views.member_tree_modern, name='member_tree_modern'),
    path('pyramid/<str:member_id>/', views.pyramid_view, name='pyramid_view'),

    # ===================== MEMBER ROUTES =====================
    path('members/', views.member_list, name='member_list'),
    path('members/login/', views.member_login, name='member_login'),
    path('members/register/', views.member_register, name='member_register'),

    # ===================== ADD MEMBER ROUTES =====================
    path('member/add/', views.add_member_form, name='add_member_form'),
    path('member/add/<str:parent_id>/<str:position>/', 
         views.add_member_under_parent, 
         name='add_member'),

    # ===================== EDIT / DELETE MEMBER =====================
    path('member/edit/<str:member_id>/', views.edit_member, name='edit_member'),
    path('member/edit-sponsor/<str:member_id>/', views.edit_sponsor, name='edit_sponsor'),
    path('member/delete/<str:member_id>/', views.delete_member, name='delete_member'),
    path('member/replace/<str:member_id>/', views.replace_member, name='replace_member'),
    path('member/<str:member_id>/bv/', views.member_bv, name='member_bv'),

    # ===================== MEMBER DETAIL POPUP (JSON) =====================
    path('member/detail-json/<str:member_id>/', views.member_detail_json, name='member_detail_json'),
    path('member/detail/<str:member_id>/', views.member_detail_json, name='member_detail_legacy'),

    # ===================== PRODUCT / CART / CHECKOUT =====================
    path('products/', views.product_list, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path("income/", views.income_report, name="income_page"),

    # ===================== COMMISSION / INCOME =====================
    path('commission/credit/<str:member_id>/', views.credit_commission, name='credit_commission'),
    path("income/export/", views.export_income_excel, name="export_income_excel"),
    path('export-income/', views.export_members_income, name='export_income'),
    path("income_report/", views.income_report, name="income_report"),
    path("income_chart/<str:member_id>/", views.income_chart, name="income_chart"),

    # ===================== RANK / SALARY REPORTS =====================
    path("rank-report/", views.rank_report, name="rank_report"),
    path("salary-report/", views.salary_report, name="salary_report"),
    path("member/<str:member_id>/rank/", views.member_rank_detail, name="member_rank_detail"),
]

# ===================== STATIC / MEDIA =====================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


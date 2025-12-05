from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'mrp',
        'distributor_id',
        'referral_code',
        'commission_percentage',
        'level',
        'parent_distributor',
        'created_at',
    )
    search_fields = ('name', 'distributor_id', 'referral_code')
    list_filter = ('level', 'commission_percentage', 'created_at')


from django.contrib import admin
from .models import Member, Payment, Income, Product

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'aadhar_number', 'left_child', 'right_child', 'sponsor')
    search_fields = ('name', 'email', 'aadhar_number')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'member', 'amount', 'status', 'date')
    search_fields = ('member__name', 'status')
    list_filter = ('status', 'date')


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'member', 'date',
        'joining_package', 'binary_pairs', 'binary_income',
        'sponsor_income', 'flash_out_bonus', 'salary_income'
    )
    search_fields = ('member__name',)
    list_filter = ('date',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'mrp', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)


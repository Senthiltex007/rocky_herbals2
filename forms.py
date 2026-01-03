from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'mrp',
            'image',
            # MLM futures
            'distributor_id',
            'referral_code',
            'commission_percentage',
            'level',
            'parent_distributor',
        ]


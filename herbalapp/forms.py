# herbalapp/forms.py

from django import forms
from .models import Member, Product


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'name',
            'email',
            'phone',
            'aadhar_number',
            'avatar',
            'district',
            'taluk',
            'pincode',
            'sponsor',      # ✅ Added (important for MLM)
            'side',         # ✅ Added (left/right placement)
        ]
        widgets = {
            'side': forms.Select(choices=[('left', 'Left'), ('right', 'Right')]),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "mrp",
            "bv_value",
            "description",
            "image"
        ]


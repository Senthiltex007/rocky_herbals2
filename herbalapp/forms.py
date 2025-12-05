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
            'package',
            'avatar',
            'district',
            'taluk',
            'pincode'
        ]
        # NOTE:
        # 'parent' and 'side' removed — these will be assigned in the view


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "mrp", "bv_value", "description", "image"]


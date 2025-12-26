from django import forms
from .models import Member, Product

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "name", "email", "phone", "aadhar_number", "avatar",
            "district", "taluk", "pincode", "placement", "sponsor",
            "side", "position", "joined_date",
        ]
        widgets = {
            "side": forms.Select(choices=[("left", "Left"), ("right", "Right")]),
            "position": forms.Select(choices=[("left", "Left"), ("right", "Right")]),
            "joined_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        required_fields = ["name", "placement", "sponsor", "side", "joined_date"]

        for field in required_fields:
            if not cleaned_data.get(field):
                raise forms.ValidationError(f"{field} is required for MLM income calculation rules.")

        side = cleaned_data.get("side")
        if side not in ["left", "right"]:
            raise forms.ValidationError("Side must be either 'left' or 'right'.")

        return cleaned_data


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "mrp", "bv_value", "description", "image"]


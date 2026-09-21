from django import forms
from .models import Ingredient, StockTransaction

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = [
            "name", "category", "quantity", "unit",
            "minimum_stock", "maximum_stock", "unit_cost",
            "supplier_fk", "supplier", "expiration_date",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "minimum_stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "maximum_stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "unit_cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "placeholder": "PHP per unit"}),
            "supplier_fk": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.TextInput(attrs={"class": "form-control", "placeholder": "Legacy free-text (use dropdown above)"}),
            "expiration_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        labels = {
            "supplier_fk": "Supplier (linked)",
            "supplier": "Supplier (legacy text)",
            "unit_cost": "Unit Cost (₱)",
        }

class StockDeductionForm(forms.Form):
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.none(),
        required=False,
        widget=forms.HiddenInput()
    )
    deduct_quantity = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-slate-700 "
                     "focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all",
            "step": "0.01", "min": "0.01"
        })
    )
    transaction_reason = forms.ChoiceField(
        choices=[
            ("NORMAL_USAGE", "Normal Usage"),
            ("SPOILAGE_WASTE", "Spoilage/Waste"),
            ("DAMAGED", "Damaged"),
            ("OTHER", "Other"),
        ],
        widget=forms.Select(attrs={
            "class": "w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-slate-700 "
                     "focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent "
                     "transition-all appearance-none bg-white",
            "required": True
        })
    )

    def __init__(self, *args, initial_ingredient=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingredient"].queryset = Ingredient.objects.order_by("name")
        if initial_ingredient:
            self.fields["ingredient"].initial = initial_ingredient
            self.fields["ingredient"].widget = forms.HiddenInput()
            self.fields["ingredient"].required = False
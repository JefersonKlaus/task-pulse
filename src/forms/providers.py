from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Provider
from .fields import provider_filter


class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ("name",)
        labels = {"name": _("Nome da empresa")}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Ex.: Alignerr")})
        }


class ProviderFilterForm(forms.Form):
    """The company filter of the project and payment lists (GET)."""

    empresa = provider_filter()

    def provider(self):
        """The chosen company; None for all, or when the choice is invalid."""
        return self.cleaned_data["empresa"] if self.is_valid() else None

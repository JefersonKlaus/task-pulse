from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("provider", "url", "name", "description")
        labels = {
            "provider": _("Empresa"),
            "url": _("URL do repositório git"),
            "name": _("Nome do projeto"),
            "description": _("Descrição"),
        }
        help_texts = {
            "name": _(
                "Opcional. Se ficar em branco, usa o nome do repositório da URL."
            ),
        }
        widgets = {
            "url": forms.TextInput(
                attrs={"placeholder": _("https://github.com/empresa/projeto.git")}
            ),
            "name": forms.TextInput(attrs={"placeholder": _("Ex.: Portal web")}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Every project belongs to one company: it is the one that pays for
        # its tasks. (Older projects may have none until they are edited.)
        self.fields["provider"].required = True
        self.fields["provider"].empty_label = _("Escolha a empresa")

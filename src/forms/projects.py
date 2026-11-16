from django import forms

from ..models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("url", "name", "description")
        labels = {
            "url": "URL do repositório git",
            "name": "Nome do projeto",
            "description": "Descrição",
        }
        help_texts = {
            "name": "Opcional. Se ficar em branco, usa o nome do repositório da URL.",
        }
        widgets = {
            "url": forms.TextInput(
                attrs={"placeholder": "https://github.com/empresa/projeto.git"}
            ),
            "name": forms.TextInput(attrs={"placeholder": "Ex.: Portal web"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

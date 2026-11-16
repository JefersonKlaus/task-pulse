from django import forms

from .models import Project, Task


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("repository", "name")
        labels = {
            "repository": "Repositório",
            "name": "Nome do projeto",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ex.: Portal web"}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("nickname", "time_spent", "language", "date")
        labels = {
            "nickname": "Nome da tarefa",
            "time_spent": "Horas",
            "language": "Linguagem",
            "date": "Data",
        }
        widgets = {
            "time_spent": forms.NumberInput(
                attrs={"step": "0.25", "min": "0", "placeholder": "Ex.: 2.5"}
            ),
            "language": forms.TextInput(attrs={"placeholder": "Ex.: Python"}),
            "date": forms.DateInput(attrs={"type": "date"}),
        }

from django import forms
from django.core.exceptions import ValidationError

from ..integrations.tasks_csv import ImportFileError, read_tasks_file
from ..models import Project
from ..services.task_import import NewProject


class TaskImportForm(forms.Form):
    """Upload a CSV of tasks into an existing project or a new one.

    Validating the form also parses the file (``rows``); importing is
    ``src.services.task_import.import_tasks``.
    """

    MAX_FILE_SIZE = 2 * 1024 * 1024
    MAX_ERRORS_SHOWN = 20

    file = forms.FileField(
        label="Arquivo CSV",
        widget=forms.FileInput(attrs={"accept": ".csv,.txt,text/csv"}),
        help_text="Colunas: date, id, time, desc, status. Separador ; , ou tab.",
    )
    project = forms.ModelChoiceField(
        label="Projeto",
        queryset=Project.objects.all(),
        required=False,
        empty_label="+ Criar novo projeto",
    )
    new_project_url = forms.CharField(
        label="URL do repositório git",
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "https://github.com/empresa/projeto.git"}
        ),
    )
    new_project_name = forms.CharField(
        label="Nome do novo projeto",
        max_length=255,
        required=False,
        help_text="Opcional. Se ficar em branco, usa o nome do repositório da URL.",
    )

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > self.MAX_FILE_SIZE:
            raise ValidationError("O arquivo tem mais de 2 MB.")
        try:
            self.rows = read_tasks_file(upload.read())
        except ImportFileError as error:
            raise ValidationError(self._limit(error.messages))
        return upload

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("project") and not cleaned_data.get("new_project_url"):
            self.add_error(
                "new_project_url",
                "Informe a URL para criar um projeto novo, "
                "ou escolha um projeto existente.",
            )
        return cleaned_data

    def destination(self):
        """The selected ``Project``, or the ``NewProject`` to create."""
        project = self.cleaned_data["project"]
        if project is not None:
            return project
        return NewProject(
            url=self.cleaned_data["new_project_url"],
            name=self.cleaned_data["new_project_name"],
        )

    def _limit(self, messages):
        if len(messages) <= self.MAX_ERRORS_SHOWN:
            return messages
        hidden = len(messages) - self.MAX_ERRORS_SHOWN
        return messages[: self.MAX_ERRORS_SHOWN] + [f"… e mais {hidden} erros."]

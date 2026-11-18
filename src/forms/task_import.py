from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from ..integrations.tasks_csv import ImportFileError, read_tasks_file
from ..models import Project, Provider
from ..services.task_import import NewProject, creates_projects


class TaskImportForm(forms.Form):
    """Upload a CSV of tasks into an existing project or a new one.

    Rows with a github repository go to that repository's project instead;
    when every row has one, no project needs to be chosen.

    Validating the form also parses the file (``rows``); importing is
    ``src.services.task_import.import_tasks``.
    """

    MAX_FILE_SIZE = 2 * 1024 * 1024
    MAX_ERRORS_SHOWN = 20

    file = forms.FileField(
        label=_("Arquivo CSV"),
        widget=forms.FileInput(attrs={"accept": ".csv,.txt,text/csv"}),
        help_text=_(
            "Colunas: date, id, time, desc, status e, opcional, github. "
            "Separador ; , ou tab."
        ),
    )
    project = forms.ModelChoiceField(
        label=_("Projeto"),
        queryset=Project.objects.all(),
        required=False,
        empty_label=_("+ Criar novo projeto"),
    )
    new_project_url = forms.CharField(
        label=_("URL do repositório do novo projeto"),
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": _("https://github.com/empresa/projeto.git")}
        ),
    )
    new_project_name = forms.CharField(
        label=_("Nome do novo projeto"),
        max_length=255,
        required=False,
        help_text=_("Opcional. Se ficar em branco, usa o nome do repositório da URL."),
    )
    provider = forms.ModelChoiceField(
        label=_("Empresa dos projetos novos"),
        queryset=Provider.objects.all(),
        required=False,
        empty_label=_("Escolha a empresa"),
        help_text=_(
            "Obrigatória quando a importação cria projetos: o novo projeto "
            "acima e os repositórios da coluna github que ainda não existem. "
            "Os projetos existentes mantêm a sua."
        ),
    )
    rows = None  # the file's rows, once it is valid

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > self.MAX_FILE_SIZE:
            raise ValidationError(_("O arquivo tem mais de 2 MB."))
        try:
            self.rows = read_tasks_file(upload.read())
        except ImportFileError as error:
            raise ValidationError(self._limit(error.messages))
        return upload

    def clean(self):
        cleaned_data = super().clean()
        # A valid file whose rows all have github needs no project.
        every_row_has_github = self.rows and all(row.github for row in self.rows)
        chosen = cleaned_data.get("project") or cleaned_data.get("new_project_url")
        if not chosen and not every_row_has_github:
            self.add_error(
                "new_project_url",
                _(
                    "Informe a URL para criar um projeto novo, ou escolha um "
                    "projeto existente para as linhas sem github."
                )
                if self.rows and any(row.github for row in self.rows)
                else _(
                    "Informe a URL para criar um projeto novo, "
                    "ou escolha um projeto existente."
                ),
            )
        # Every project belongs to a company: new ones need it.
        if (
            self.rows
            and not self.errors
            and cleaned_data.get("provider") is None
            and creates_projects(self.rows, self.destination())
        ):
            self.add_error(
                "provider", _("Escolha a empresa dos projetos que serão criados.")
            )
        return cleaned_data

    def destination(self):
        """The selected ``Project``, the ``NewProject`` to create, or None."""
        project = self.cleaned_data["project"]
        if project is not None:
            return project
        if not self.cleaned_data["new_project_url"]:
            return None
        return NewProject(
            url=self.cleaned_data["new_project_url"],
            name=self.cleaned_data["new_project_name"],
            provider=self.cleaned_data["provider"],
        )

    def _limit(self, messages):
        if len(messages) <= self.MAX_ERRORS_SHOWN:
            return messages
        hidden = len(messages) - self.MAX_ERRORS_SHOWN
        return messages[: self.MAX_ERRORS_SHOWN] + [
            ngettext(
                "… e mais %(count)s erro.", "… e mais %(count)s erros.", hidden
            )
            % {"count": hidden}
        ]

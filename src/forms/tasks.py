from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..domain.task_status import TaskStatus
from ..models import Task
from .fields import HoursMinutesField, date_input

LABELS = {
    "name": _("Nome da tarefa"),
    "external_id": _("ID externo"),
    "description": _("Descrição (objetivos)"),
    "acceptance_criteria": _("Como validar a conclusão"),
    "status": _("Status"),
    "started_on": _("Início"),
    "finished_on": _("Término"),
}

WIDGETS = {
    "description": forms.Textarea(attrs={"rows": 3}),
    "acceptance_criteria": forms.Textarea(
        attrs={"rows": 3, "placeholder": _("Ex.: os testes de login passam")}
    ),
    "started_on": date_input(),
    "finished_on": date_input(),
}


class TaskCreateForm(forms.ModelForm):
    """New task: it starts as DOING, today, with no finish date and no time."""

    class Meta:
        model = Task
        fields = ("name", "description", "acceptance_criteria")
        labels = LABELS
        widgets = WIDGETS


class TaskUpdateForm(forms.ModelForm):
    """Existing task: every field can be edited.

    * Time: "Tempo total" can be rewritten, and "Adicionar tempo" is added on
      top of it when the form is saved.
    * The finish date can only be entered once the task has left DOING.
      While the selected status is DOING the field is disabled, so Django
      ignores any submitted value.
    """

    LOCKED_WHILE_DOING = ("finished_on",)

    minutes_spent = HoursMinutesField(
        label=_("Tempo total"),
        help_text=_("Apague e digite o total correto, se precisar corrigir."),
    )
    add_time = HoursMinutesField(
        label=_("Adicionar tempo"),
        required=False,
        allow_zero=False,
        help_text=_("Somado ao tempo total ao salvar."),
    )

    class Meta:
        model = Task
        fields = (
            "name",
            "external_id",
            "description",
            "acceptance_criteria",
            "started_on",
            "status",
            "finished_on",
            "minutes_spent",
            "add_time",
        )
        labels = LABELS
        widgets = WIDGETS
        help_texts = {
            "finished_on": _(
                "Preenchida automaticamente ao mudar o status para Review ou "
                "Done. Só pode ser informada quando o status não é Doing."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.selected_status() == TaskStatus.DOING:
            for name in self.LOCKED_WHILE_DOING:
                self.fields[name].disabled = True

    def selected_status(self):
        """The status being submitted, or the task's current one."""
        if self.is_bound:
            return self.data.get(self.add_prefix("status"))
        return self.initial.get("status", self.instance.status)

    def clean_external_id(self):
        # `project` is not a form field, so Django skips the per-project
        # unique constraint; check it here to show an error, not crash.
        external_id = self.cleaned_data["external_id"]
        duplicate = (
            external_id
            and Task.objects.filter(
                project_id=self.instance.project_id, external_id=external_id
            )
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if duplicate:
            raise ValidationError(
                _("Já existe uma tarefa com este ID externo neste projeto.")
            )
        return external_id

    def clean(self):
        cleaned_data = super().clean()
        added = cleaned_data.get("add_time")
        total = cleaned_data.get("minutes_spent")
        if added and total is not None:
            cleaned_data["minutes_spent"] = total + added
        return cleaned_data


class TaskAddTimeForm(forms.Form):
    """Quick "add time" box next to each task on the project page."""

    time = HoursMinutesField(label=_("Adicionar tempo"), allow_zero=False)

"""Read the CSV file of tasks exported by another system.

Expected columns (header names are case-insensitive, any order; extra
columns are ignored), one task per line:

    date;id;time;desc;status;github
    16/11/2026;TP-101;3,8;Tela de login;DONE;acme/portal

* ``date``   dd/mm/aaaa or aaaa-mm-dd.
* ``id``     the task's id in the other system (required; unique per project
             in the file, since issue numbers repeat across repositories).
* ``time``   hours with a comma or a dot ("3,8" = 3:48) or H:MM. Blank = 0.
* ``desc``   the task name.
* ``status`` DOING, REVIEW, DONE or REJECTED (or their labels). Blank = DOING.
* ``github`` optional column: the repository of the task's project, as a URL
             or as "owner/repository". Blank (or no column) = the project
             chosen in the form.

The separator (";", "," or tab) is detected from the header line. The file
may be UTF-8 (with or without BOM) or Windows-1252, the Excel default.

The whole file is validated and every problem is reported with its line
number, so a file with errors is never half-imported. Turning rows into
tasks is ``src.services.task_import``'s job.
"""

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from django.utils.translation import gettext as _

from ..domain.durations import parse_decimal_hours, parse_hmm
from ..domain.git_urls import repository_key, repository_url
from ..domain.task_status import TaskStatus
from ..models import Project, Task

REQUIRED_COLUMNS = ("date", "id", "time", "desc", "status")
OPTIONAL_COLUMNS = ("github",)
DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")
DELIMITERS = (";", ",", "\t")
EXTERNAL_ID_MAX_LENGTH = Task._meta.get_field("external_id").max_length
URL_MAX_LENGTH = Project._meta.get_field("url").max_length

# "done", "Done", "DONE" and the Portuguese label "Rejeitado" all map to the
# value. Fixed words, not the (translated) labels: the file format is the
# same whatever the language of the interface.
STATUS_BY_TEXT = {
    **{value.lower(): value for value in TaskStatus.values},
    "rejeitado": TaskStatus.REJECTED,
}


class ImportFileError(Exception):
    """The file cannot be imported; ``messages`` lists every problem found."""

    def __init__(self, messages):
        super().__init__("\n".join(messages))
        self.messages = list(messages)


@dataclass(frozen=True)
class ImportedRow:
    external_id: str
    date: date
    minutes: int
    desc: str
    status: str
    # The repository URL of the task's project ("owner/repo" expanded);
    # "" = the project chosen in the form.
    github: str = ""


def read_tasks_file(data):
    """Parse and validate the raw bytes of an uploaded file.

    Returns a list of ``ImportedRow``; raises ``ImportFileError`` listing all
    problems if anything is wrong.
    """
    text = _decode(data)
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise ImportFileError([_("O arquivo está vazio.")])

    reader = csv.reader(io.StringIO(text), delimiter=_detect_delimiter(lines[0]))
    header = [name.strip().lower() for name in next(reader)]
    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        raise ImportFileError(
            [
                _(
                    "Colunas obrigatórias ausentes: %(missing)s. "
                    "O cabeçalho deve ter: %(required)s."
                )
                % {
                    "missing": ", ".join(missing),
                    "required": ", ".join(REQUIRED_COLUMNS),
                }
            ]
        )
    positions = {
        column: header.index(column)
        for column in REQUIRED_COLUMNS + OPTIONAL_COLUMNS
        if column in header
    }

    rows, errors, first_line_by_id = [], [], {}
    for values in reader:
        if not any(value.strip() for value in values):
            continue  # blank line
        record = {
            column: values[index].strip() if index < len(values) else ""
            for column, index in positions.items()
        }
        record.setdefault("github", "")
        row, problems = _parse_row(record)
        external_id = record["id"]
        # An id repeats only within the same project: the same repository
        # (however written), or the form's project for a blank github.
        key = (repository_key(row.github) if row else record["github"], external_id)
        if key in first_line_by_id:
            problems.append(
                _("id “%(id)s” repetido (já aparece na linha %(line)s)")
                % {"id": external_id, "line": first_line_by_id[key]}
            )
        elif external_id:
            first_line_by_id[key] = reader.line_num
        if problems:
            errors.append(
                _("Linha %(line)s: %(problems)s.")
                % {"line": reader.line_num, "problems": "; ".join(problems)}
            )
        else:
            rows.append(row)

    if errors:
        raise ImportFileError(errors)
    if not rows:
        raise ImportFileError([_("O arquivo não tem linhas de tarefas.")])
    return rows


def _parse_row(record):
    problems = []

    external_id = record["id"]
    if not external_id:
        problems.append(_("id vazio"))
    elif len(external_id) > EXTERNAL_ID_MAX_LENGTH:
        problems.append(
            _("id com mais de %(max)s caracteres") % {"max": EXTERNAL_ID_MAX_LENGTH}
        )

    task_date = _parse_date(record["date"])
    if task_date is None:
        problems.append(
            _("data inválida “%(value)s” (use dd/mm/aaaa)")
            % {"value": record["date"]}
        )

    minutes = _parse_time(record["time"])
    if minutes is None:
        problems.append(
            _("tempo inválido “%(value)s” (use 3,8 ou 3:48)")
            % {"value": record["time"]}
        )

    desc = record["desc"]
    if not desc:
        problems.append(_("desc vazio"))

    status = STATUS_BY_TEXT.get(record["status"].lower() or "doing")
    if status is None:
        problems.append(
            _("status inválido “%(value)s” (use %(choices)s)")
            % {"value": record["status"], "choices": ", ".join(TaskStatus.values)}
        )

    github = record["github"]
    if github:
        try:
            github = repository_url(github)
        except ValueError:
            problems.append(
                _(
                    "github inválido “%(value)s” "
                    "(use dono/repositorio ou a URL do repositório)"
                )
                % {"value": github}
            )
        else:
            if len(github) > URL_MAX_LENGTH:
                problems.append(
                    _("github com mais de %(max)s caracteres") % {"max": URL_MAX_LENGTH}
                )

    if problems:
        return None, problems
    return (
        ImportedRow(external_id, task_date, minutes, desc, status, github),
        problems,
    )


def _parse_date(value):
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def _parse_time(value):
    if not value:
        return 0
    for parse in (parse_decimal_hours, parse_hmm):
        try:
            return parse(value)
        except ValueError:
            continue
    return None


def _decode(data):
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _detect_delimiter(header_line):
    """The header has no decimal commas, so its most frequent separator wins."""
    return max(DELIMITERS, key=header_line.count)

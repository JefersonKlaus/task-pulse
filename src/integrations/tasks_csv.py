"""Read the CSV file of tasks exported by another system.

Expected columns (header names are case-insensitive, any order; extra
columns are ignored), one task per line:

    date;id;time;desc;status
    16/11/2026;TP-101;3,8;Tela de login;DONE

* ``date``   dd/mm/aaaa or aaaa-mm-dd.
* ``id``     the task's id in the other system (required, unique in the file).
* ``time``   hours with a comma or a dot ("3,8" = 3:48) or H:MM. Blank = 0.
* ``desc``   the task name.
* ``status`` DOING, REVIEW, DONE or REJECTED (or their labels). Blank = DOING.

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

from ..domain.durations import parse_decimal_hours, parse_hmm
from ..domain.task_status import TaskStatus
from ..models import Task

REQUIRED_COLUMNS = ("date", "id", "time", "desc", "status")
DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")
DELIMITERS = (";", ",", "\t")
EXTERNAL_ID_MAX_LENGTH = Task._meta.get_field("external_id").max_length

# "done", "Done", "DONE" and the labels ("Rejeitado") all map to the value.
STATUS_BY_TEXT = {
    **{label.lower(): value for value, label in TaskStatus.choices},
    **{value.lower(): value for value in TaskStatus.values},
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


def read_tasks_file(data):
    """Parse and validate the raw bytes of an uploaded file.

    Returns a list of ``ImportedRow``; raises ``ImportFileError`` listing all
    problems if anything is wrong.
    """
    text = _decode(data)
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise ImportFileError(["O arquivo está vazio."])

    reader = csv.reader(io.StringIO(text), delimiter=_detect_delimiter(lines[0]))
    header = [name.strip().lower() for name in next(reader)]
    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        raise ImportFileError(
            [
                f"Colunas obrigatórias ausentes: {', '.join(missing)}. "
                f"O cabeçalho deve ter: {', '.join(REQUIRED_COLUMNS)}."
            ]
        )
    positions = {column: header.index(column) for column in REQUIRED_COLUMNS}

    rows, errors, first_line_by_id = [], [], {}
    for values in reader:
        if not any(value.strip() for value in values):
            continue  # blank line
        record = {
            column: values[index].strip() if index < len(values) else ""
            for column, index in positions.items()
        }
        row, problems = _parse_row(record)
        external_id = record["id"]
        if external_id in first_line_by_id:
            problems.append(
                f"id “{external_id}” repetido "
                f"(já aparece na linha {first_line_by_id[external_id]})"
            )
        elif external_id:
            first_line_by_id[external_id] = reader.line_num
        if problems:
            errors.append(f"Linha {reader.line_num}: {'; '.join(problems)}.")
        else:
            rows.append(row)

    if errors:
        raise ImportFileError(errors)
    if not rows:
        raise ImportFileError(["O arquivo não tem linhas de tarefas."])
    return rows


def _parse_row(record):
    problems = []

    external_id = record["id"]
    if not external_id:
        problems.append("id vazio")
    elif len(external_id) > EXTERNAL_ID_MAX_LENGTH:
        problems.append(f"id com mais de {EXTERNAL_ID_MAX_LENGTH} caracteres")

    task_date = _parse_date(record["date"])
    if task_date is None:
        problems.append(f"data inválida “{record['date']}” (use dd/mm/aaaa)")

    minutes = _parse_time(record["time"])
    if minutes is None:
        problems.append(f"tempo inválido “{record['time']}” (use 3,8 ou 3:48)")

    desc = record["desc"]
    if not desc:
        problems.append("desc vazio")

    status = STATUS_BY_TEXT.get(record["status"].lower() or "doing")
    if status is None:
        problems.append(
            f"status inválido “{record['status']}” "
            f"(use {', '.join(TaskStatus.values)})"
        )

    if problems:
        return None, problems
    return ImportedRow(external_id, task_date, minutes, desc, status), problems


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

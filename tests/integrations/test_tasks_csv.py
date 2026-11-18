from collections import Counter
from datetime import date
from pathlib import Path

from django.test import SimpleTestCase

from src.integrations.tasks_csv import ImportedRow, ImportFileError, read_tasks_file

HEADER = "date;id;time;desc;status"


def csv_bytes(*lines, header=HEADER, encoding="utf-8"):
    return "\n".join((header, *lines)).encode(encoding) + b"\n"


def read_one(data):
    (row,) = read_tasks_file(data)
    return row


class ReadTasksFileTests(SimpleTestCase):
    """What a valid file can look like."""

    def test_reads_every_column(self):
        self.assertEqual(
            read_one(csv_bytes("16/11/2026;TP-101;3,8;Tela de login;DONE")),
            ImportedRow("TP-101", date(2026, 11, 16), 228, "Tela de login", "DONE"),
        )

    def test_detects_the_separator(self):
        for data in (
            b"date;id;time;desc;status\n16/11/2026;A;3,8;Login;DONE\n",
            b'date,id,time,desc,status\n16/11/2026,A,"3,8",Login,DONE\n',
            b"date\tid\ttime\tdesc\tstatus\n16/11/2026\tA\t3,8\tLogin\tDONE\n",
        ):
            with self.subTest(data=data[:10]):
                self.assertEqual(read_one(data).minutes, 228)

    def test_reads_utf8_with_bom_and_excel_windows_1252(self):
        for data in (
            "\ufeff".encode() + csv_bytes("16/11/2026;A;1;Revisão;DONE"),
            csv_bytes("16/11/2026;A;1;Revisão;DONE", encoding="cp1252"),
        ):
            with self.subTest(data=data[:3]):
                self.assertEqual(read_one(data).desc, "Revisão")

    def test_header_is_flexible(self):
        # any case, any order, extra columns ignored; values trimmed
        data = csv_bytes(
            " done ; Login ; A ; 2026-11-16 ; 1 ; Ana",
            header="STATUS;Desc;Id;DATE;time;dono",
        )
        self.assertEqual(
            read_one(data), ImportedRow("A", date(2026, 11, 16), 60, "Login", "DONE")
        )

    def test_time_formats(self):
        for time, minutes in (("3,8", 228), ("3.8", 228), ("3:48", 228), ("", 0)):
            with self.subTest(time=time):
                row = read_one(csv_bytes(f"16/11/2026;A;{time};T;DONE"))
                self.assertEqual(row.minutes, minutes)

    def test_status_values(self):
        for text, status in (
            ("review", "REVIEW"),
            ("Rejeitado", "REJECTED"),
            ("", "DOING"),
        ):
            with self.subTest(text=text):
                row = read_one(csv_bytes(f"16/11/2026;A;1;T;{text}"))
                self.assertEqual(row.status, status)

    def test_missing_values_at_the_end_of_a_line_are_blank(self):
        # Some tools drop trailing empty cells: no status means DOING.
        self.assertEqual(
            read_one(csv_bytes("16/11/2026;A;1;Login")),
            ImportedRow("A", date(2026, 11, 16), 60, "Login", "DOING"),
        )

    def test_skips_blank_lines(self):
        rows = read_tasks_file(
            csv_bytes("16/11/2026;A;1;T;DONE", "", ";;;;", "16/11/2026;B;1;T;DONE")
        )
        self.assertEqual([row.external_id for row in rows], ["A", "B"])


class ReadTasksFileErrorTests(SimpleTestCase):
    """Every problem is reported with its line number; nothing is returned."""

    def errors(self, data):
        with self.assertRaises(ImportFileError) as raised:
            read_tasks_file(data)
        return raised.exception.messages

    def test_lists_every_problem_of_a_line(self):
        self.assertEqual(
            self.errors(csv_bytes("xx;;abc;;X")),
            [
                "Linha 2: id vazio; data inválida “xx” (use dd/mm/aaaa); "
                "tempo inválido “abc” (use 3,8 ou 3:48); desc vazio; "
                "status inválido “X” (use DOING, REVIEW, DONE, REJECTED)."
            ],
        )

    def test_reports_every_invalid_line_with_its_number(self):
        errors = self.errors(
            csv_bytes(
                "31/02/2026;A;1;T;DONE", "", "16/11/2026;B;1;T;DONE", "yy;C;1;T;DONE"
            )
        )
        self.assertEqual([e.split(":")[0] for e in errors], ["Linha 2", "Linha 5"])

    def test_duplicate_id_points_to_the_first_line(self):
        self.assertEqual(
            self.errors(csv_bytes("16/11/2026;A;1;T;DONE", "17/11/2026;A;2;U;DONE")),
            ["Linha 3: id “A” repetido (já aparece na linha 2)."],
        )

    def test_empty_ids_are_not_reported_as_repeated(self):
        self.assertEqual(
            self.errors(csv_bytes("16/11/2026;;1;T;DONE", "16/11/2026;;1;U;DONE")),
            ["Linha 2: id vazio.", "Linha 3: id vazio."],
        )

    def test_id_longer_than_100_characters(self):
        self.assertEqual(
            self.errors(csv_bytes(f"16/11/2026;{'x' * 101};1;T;DONE")),
            ["Linha 2: id com mais de 100 caracteres."],
        )

    def test_files_that_are_not_a_task_list(self):
        for data, message in (
            (b"", "O arquivo está vazio."),
            (
                b"date;id;desc\n16/11/2026;A;T\n",
                "Colunas obrigatórias ausentes: time, status. "
                "O cabeçalho deve ter: date, id, time, desc, status.",
            ),
            (csv_bytes(), "O arquivo não tem linhas de tarefas."),
        ):
            with self.subTest(message=message):
                self.assertEqual(self.errors(data), [message])


SAMPLE_FILE = Path(__file__).resolve().parents[1] / "fixtures" / "tarefas_exemplo.csv"


class GithubColumnTests(SimpleTestCase):
    """The optional github column: the repository of each task's project."""

    def rows(self, *lines, header="date;id;time;desc;status;github"):
        return read_tasks_file(csv_bytes(*lines, header=header))

    def test_reads_the_repository_of_each_row(self):
        rows = self.rows(
            "16/11/2026;A;1;Login;DONE;acme/portal",
            "16/11/2026;B;1;API;DONE;https://github.com/acme/api.git",
            "16/11/2026;C;1;Revisão;DONE;",
        )
        self.assertEqual(
            [row.github for row in rows],
            [
                "https://github.com/acme/portal",  # short form expanded
                "https://github.com/acme/api.git",
                "",  # the project chosen in the form
            ],
        )

    def test_is_optional_and_can_be_anywhere(self):
        (without,) = self.rows("16/11/2026;A;1;Login;DONE", header=HEADER)
        self.assertEqual(without.github, "")
        (first,) = self.rows(
            "acme/portal;16/11/2026;A;1;Login;DONE",
            header="GitHub;date;id;time;desc;status",
        )
        self.assertEqual(first.github, "https://github.com/acme/portal")

    def test_an_id_repeats_only_within_the_same_repository(self):
        rows = self.rows(
            "16/11/2026;12;1;Login;DONE;acme/portal",
            "16/11/2026;12;1;Login;DONE;acme/api",  # issue 12 of another repo
            "16/11/2026;12;1;Login;DONE;",  # the form's project
        )
        self.assertEqual(len(rows), 3)
        with self.assertRaises(ImportFileError) as raised:
            self.rows(
                "16/11/2026;12;1;Login;DONE;acme/portal",
                "16/11/2026;12;1;Login;DONE;https://github.com/Acme/portal.git",
            )
        self.assertEqual(
            raised.exception.messages,
            ["Linha 3: id “12” repetido (já aparece na linha 2)."],
        )

    def test_invalid_repositories(self):
        with self.assertRaises(ImportFileError) as raised:
            self.rows(
                "16/11/2026;A;1;Login;DONE;portal",
                f"16/11/2026;B;1;Login;DONE;acme/{'x' * 250}",
            )
        self.assertEqual(
            raised.exception.messages,
            [
                "Linha 2: github inválido “portal” "
                "(use dono/repositorio ou a URL do repositório).",
                "Linha 3: github com mais de 255 caracteres.",
            ],
        )


class SampleFileTests(SimpleTestCase):
    """tests/fixtures/tarefas_exemplo.csv, for trying the import by hand."""

    def test_is_valid_and_varied(self):
        rows = read_tasks_file(SAMPLE_FILE.read_bytes())
        self.assertEqual(len(rows), 35)
        self.assertEqual(
            {row.status for row in rows}, {"DOING", "REVIEW", "DONE", "REJECTED"}
        )
        without_time = [row for row in rows if row.minutes == 0]
        self.assertEqual(len(without_time), 8)
        # Most lines go to the chosen project; 6 name a repository, written
        # in each accepted way (short form, https URL, SSH URL).
        self.assertEqual(
            Counter(row.github for row in rows),
            {
                "": 29,
                "https://github.com/acme/cotacao-api": 4,
                "git@github.com:acme/graficos.git": 2,
            },
        )

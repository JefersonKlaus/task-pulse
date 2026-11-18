# Task Pulse

A Django app to plan and log work on software projects. Each project is a git
repository with tasks (goals, how to validate them, dates, time spent and
status). Tasks can be imported from a CSV file. The billing page
(Faturamento) calculates the hours and the earnings of a period in US
dollars and Brazilian reais, and registers payments; the statistics page
(Estatísticas) charts hours, tasks and money over time. Projects belong to
companies (Alignerr, Etho, …), and every report can be filtered by company.

The interface is in Brazilian Portuguese or in English: see
[Languages](#languages).

- [Quick start](#quick-start)
- [Using the app](#using-the-app)
- [Languages](#languages)
- [Running the tests](#running-the-tests)
- [Project structure](#project-structure)
- [Configuration](#configuration)
- [Upgrading an existing database](#upgrading-an-existing-database)
- [Known limitations](#known-limitations)

## Quick start

You need Python 3.10 or newer (Django 4.2 also runs on Python 3.8 and 3.9).

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt  # the app + test tools

python manage.py migrate
python manage.py createsuperuser     # optional, for /admin/
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The sidebar links to every page. On a phone
it is hidden: the ☰ button at the top opens it.

`requirements.txt` has only what the app needs to run (Django), and
`requirements-dev.txt` adds the test tools.

## Using the app

| Page               | URL                      |
|--------------------|--------------------------|
| Statistics         | `/estatisticas/`         |
| Billing            | `/faturamento/`          |
| Payments           | `/pagamentos/`           |
| Export payments    | `/pagamentos/exportar/`  |
| Projects           | `/` (`/?empresa=<id>`)   |
| Companies          | `/empresas/`             |
| New company        | `/empresas/nova/`        |
| Edit company       | `/empresas/<id>/editar/` |
| New project        | `/projetos/novo/`        |
| Project and tasks  | `/projetos/<id>/`        |
| Edit project       | `/projetos/<id>/editar/` |
| Edit task          | `/tarefas/<id>/editar/`  |
| Import tasks       | `/importar/`             |
| Admin              | `/admin/`                |

### Companies

The companies you work for (Alignerr, Etho, CompanyABC, …), on **Empresas**
(*Companies*, in the sidebar).

- Add a company with its name; names are unique, whatever the case
  (`Etho` = `etho`). Rename it with **Editar**. A company opens its projects.
- Each project belongs to one company, chosen on the project's form
  (**Empresa**, required): the company pays for the project's tasks. Projects
  created before companies existed show **Sem empresa** (*no company*) until
  you edit them, which asks for one. Their tasks can't be paid until then.
- Every report has an **Empresa** filter (shown once a company exists):
  Faturamento, Pagamentos (and its CSV export), Estatísticas and the project
  list. "Todas as empresas" (*all companies*) shows everything.
- A payment's company is the company of **all** its tasks' projects. It is
  not stored, so payments made before the projects had a company get it as
  soon as they do. A payment with tasks of several companies (or of a company
  and of none) is shown as **Várias empresas** (*several companies*) and is
  only listed under "Todas as empresas". Payments registered now always have
  one company (see [Payments](#payments)); only older ones can mix.
- To delete a company, use the admin (`/admin/tasks/provider/`): its projects
  stay, without a company.

### Projects

- Create a project from its git URL (https or SSH). If you leave the name
  blank, the repository's name is used:
  `https://github.com/acme/task-pulse.git` → `task-pulse`.
- On the project page the URL is a link only when it starts with `http://` or
  `https://`. SSH URLs are shown as text.

### Tasks

- **Nova tarefa** on the project page opens the form: name, goals and how to
  validate the task. A new task starts as **DOING**, with today as its start
  date (**Início**).
- **Editar** changes any field, in this order: Início → Status → Término →
  Tempo.
- The finish date (**Término**) follows the status:

  | When the status…           | Término                                    |
  |----------------------------|--------------------------------------------|
  | moves into REVIEW or DONE  | today, unless you type a date yourself     |
  | goes from REVIEW to DONE   | stays as it was                            |
  | is DOING                   | empty (the field is locked)                |
  | is REJECTED                | whatever you type                          |

  Both dates can be corrected later.

### Time

- Time is typed as `H:MM`. The **+ Tempo** box next to each task adds to its
  total: `2:00`, then `1:00`, gives `3:00`.
- On the edit page, rewrite **Tempo total** to correct the total, or fill in
  **Adicionar tempo** to add to it.
- Totals are shown in decimal hours: `3:30` → `3.50h`. Time is stored in whole
  minutes, so repeated additions stay exact.

### Importing tasks from CSV

On **Importar tarefas** (*Import tasks*), upload the file. The file has one
task per line; the `github` column is optional:

```
date;id;time;desc;status;github
16/11/2026;TP-101;3,8;Tela de login;DONE;acme/portal
17/11/2026;TP-102;1,5;API de tarefas;DOING;https://github.com/acme/api
18/11/2026;TP-103;2:00;Revisão do layout;REVIEW;
```

| Column   | Meaning                                                              |
|----------|----------------------------------------------------------------------|
| `date`   | `dd/mm/aaaa` or `aaaa-mm-dd`. The start date, and also the finish date unless the status is DOING |
| `id`     | The task's id in the other system. Required, and unique per project in the file |
| `time`   | Hours: `3,8`, `3.8` or `3:48` (all 3h48). Blank means 0             |
| `desc`   | The task name                                                        |
| `status` | `DOING`, `REVIEW`, `DONE` or `REJECTED`, in any case. Blank means DOING |
| `github` | Optional. The repository of the task's project: `owner/repo` or a URL (https or SSH). Blank means the project chosen in the form |

- **Which project receives each line.** A line with `github` goes to that
  repository's project (see below). Under **Projeto das linhas sem github**
  (*project for the lines without github*), pick an existing project, or leave
  **+ Criar novo projeto** selected and enter its git URL: it receives only the
  lines **without** github, or every line if the file has no `github` column.
  If every line has github, leave it blank.
- **Empresa dos projetos novos** (*company of the new projects*): the company
  of the projects the import creates (the new project of the form and the
  `github` repositories that don't exist yet). It is required when the import
  creates a project. Existing projects keep theirs.
- The separator can be `;`, `,` or tab. The file can be UTF-8 or Excel's
  Windows-1252, up to 2 MB. Header names may be in any order and case.
- **All or nothing**: if any line is invalid, nothing is imported, and every
  problem is listed with its line number.
- A line whose `id` already exists in its project is **skipped**, so
  importing the same file again never changes existing tasks.
- **github**: a line with a repository goes to the project of that
  repository, whatever was chosen in the form; if there is none, it is
  created, named after the repository (`acme/portal` → `portal`, URL
  `https://github.com/acme/portal`). One file can fill several projects.
  - A repository matches an existing project however the URL is written:
    `acme/portal`, `https://github.com/Acme/Portal.git` and
    `git@github.com:acme/portal.git` are the same. If two projects have the
    same repository, the oldest is used.
  - Lines without github go to the project chosen in the form. If every
    line has one, no project needs to be chosen (and none is created).
  - The same `id` may appear once per repository (GitHub issue numbers
    repeat across repositories).
  - After the import, the project's page opens; when the file filled
    several projects, the project list opens, with a line per project.
- To try it, import `tests/fixtures/tarefas_exemplo.csv`: 35 tasks from
  September to November 2026 with every status, 8 of them without time, both
  date formats, all three time formats and a desc with `;`. 6 lines have
  `github`, in each accepted way: 4 go to `acme/cotacao-api` (written as
  `acme/cotacao-api` and as its https URL) and 2 to an SSH URL
  (`git@github.com:acme/graficos.git`); the other 29 go to the project chosen
  in the form. A test imports it, so it stays valid.

### Statistics

**Estatísticas** charts a period (the last 12 months on the first visit),
by month or by week, of one company or of all (then with a chart of the
hours **by company**):

- Cards with the **hours** worked (and how many are not paid yet), the
  **tasks** (and how many are Done), the money **received** in dollars and
  the **average per hour paid** (received ÷ hours of the tasks paid).
- Charts of the hours (paid and unpaid), the tasks by status, the dollars
  received, and the hours by project (the 7 largest, then "Outros").
- Tasks count in the month or week of their start date, as on the billing
  page. Money counts in the month or week the payment was **registered**.
- Hover a bar for its values. **Ver tabela** lists every number of the
  charts (on a phone, where there is no hover, use the table).
- At most 60 bars: a longer period must be grouped by month.
- The charts are plain HTML and CSS, drawn on the server: no JavaScript
  library and no internet access.

### Billing

On **Faturamento** (called *Painel* before; `/painel/` still leads here,
filter included), choose a company (or all), a period, the statuses to include and, optionally, the
rates in US dollars. Hover over a field to see its help.

- A task belongs to the period of its start date. Only the checked statuses
  are listed and calculated; if none is checked, all are.
- **Incluir tarefas pagas** (under *Pagamento*) lists the tasks that were
  already paid together with the others, tagged **Pago**. Unchecked, paid
  tasks are left out of the list *and* of every total, and a note says they
  are hidden. It is checked on the first visit. What is left to pay (see
  [Payments](#payments)) is the same either way.
- **Valor/h** pays every hour. **Valor flat/h** pays the *last* hour of each
  task that was not rejected. Example with $90/h and a $100 flat:

  | Task                   | Value                          |
  |------------------------|--------------------------------|
  | 5h, no flat            | 5 × 90 = **$450**              |
  | 5h, with the flat      | 4 × 90 + 1 × 100 = **$460**    |
  | 0:45, with the flat    | 0.75 × 100 = **$75**           |
  | 5h, REJECTED           | 5 × 90 = **$450** (never flat) |

- **Bônus** is added once to the period's total: $460 + $40 = **$500**.
- The total in reais uses the current USD→BRL rate from
  [AwesomeAPI](https://docs.awesomeapi.com.br/api-de-moedas). The rate is
  cached for 10 minutes. This is the only part of the app that needs internet
  access. If the API can't be reached, the page shows the dollar total and a
  warning.
- The filter is part of the URL, so a view can be bookmarked:
  `/faturamento/?inicio=2026-11-01&fim=2026-11-30&status=DONE&valor_hora=90&pagas=on`.
  Leave out `pagas=on` to hide the paid tasks (a browser sends nothing for
  an unchecked box).

### Payments

Once the billing page has a **Valor/h**, a bar under the totals shows what is
still to pay. Payments are made **by a company**: the **Pagar** button appears
once a company is chosen in the filter (with "Todas as empresas" the bar only
says so), and the payment covers that company's tasks. With "Todas as
empresas", a warning counts the unpaid tasks of projects without a company,
which can't be paid until their project gets one.

1. **Pagar** opens a dialog with the period, the number of tasks, the hours
   and the estimated value in dollars and in reais.
2. Fill in what you actually received, **Pago (US$)** and **Pago (R$)**, and
   press **Confirmar pagamento**.
3. A payment is registered with the period, the estimated values, the paid
   values and its tasks, and those tasks are marked **Pago** on the
   billing page.

- A payment covers the listed tasks that are **not paid yet**. Tasks paid
  before stay on the list with the **Pago** tag, but are left out of the new
  payment and its estimate, so a task is never paid twice. When every listed
  task is paid, the button is not shown.
- The estimate includes the bonus, and is calculated again when you confirm.
  The estimate in reais is empty if the exchange rate was unavailable.
- If the tasks to pay changed after the dialog was opened (a task was
  added, or paid from another tab), nothing is saved and the billing page shows
  a message. Check the values and press **Pagar** again.
- **Pagamentos** (`/pagamentos/`, in the sidebar) lists every payment, newest
  first: when it was registered, its period, tasks and hours, and the
  estimated and paid values in dollars and reais, with the difference
  (paid − estimated, in red when less was received). **Ver tarefas** shows a
  payment's tasks.
- It shows **10 payments per page**, with page links under the table
  (`/pagamentos/?pagina=2`). The cards at the top total **every** payment;
  the table's last row totals only the payments on the page ("Total desta
  página"). A page number that doesn't exist shows the nearest page.
- **Exportar CSV** (next to the title) downloads every payment, not only
  the page's, as `pagamentos-<today>.csv`: one line per payment, newest
  first, with the table's columns and the company (**Empresa**: its name,
  "Várias empresas", or empty). It is written for Excel in Portuguese:
  `;` separator, decimal comma and no currency symbol (`12345,60`), so the
  values can be added up; dates as `dd/mm/aaaa`; UTF-8 with a BOM, for the
  accents. An estimate in reais that doesn't exist is left empty. There is
  no total line; the spreadsheet can sum the columns.

  ```
  Registrado em;Empresa;Início;Fim;Tarefas;Horas;Estimado (US$);Estimado (R$);Pago (US$);Pago (R$);Diferença (US$);Diferença (R$)
  17/11/2026 14:30;Alignerr;01/11/2026;30/11/2026;2;7,75;460,00;2461,00;450,00;2400,00;-10,00;-61,00
  ```
- **Empresa** shows only a company's payments: the cards, the table, the
  page links and the export all follow the filter. Each payment shows its
  company.
- To undo a payment, delete it in the admin (`/admin/tasks/payment/`): its
  tasks become unpaid again.

## Languages

The switch at the top right of every page (**PT | EN**; in the top bar on a
phone) changes the language of the whole interface: pages, messages, form
errors and chart labels. The choice is kept in a cookie (`django_language`).
Before one is chosen, the browser's language decides (English for an English
browser), and Portuguese otherwise.

What does not change with the language:

- Amounts keep their currency's style (`US$ 1,234.50`, `R$ 1.234,50`) and
  dates are `dd/mm/aaaa`.
- The files: the import's columns and values (`date;id;…`, `Rejeitado`) and
  the payments export (written for Excel in Portuguese).
- The addresses (`/faturamento/`, `/pagamentos/`, …) and the data you type.

### Translating

Portuguese is the source language: texts are written in Portuguese in the
code (`gettext`, `gettext_lazy`) and in the templates (`{% translate %}`,
`{% blocktranslate %}`). The English texts are in
`src/locale/en/LC_MESSAGES/django.po`; Django reads the compiled
`django.mo` next to it, which is committed, so running the app needs nothing
else.

After adding or changing a text (this needs [GNU gettext](https://www.gnu.org/software/gettext/)):

```bash
python manage.py makemessages -l en    # adds the new texts to django.po
# translate the new entries (and the ones marked "fuzzy") in django.po
python manage.py compilemessages       # updates django.mo
```

`tests/test_translations.py` fails if a text has no English translation, if
a translation isn't used anymore, or if `gettext` is called with something
other than literal text (`makemessages` only finds literal text). It can't
see text typed in a template without `{% translate %}`: that text stays in
Portuguese in English.

## Running the tests

The suite has about 310 tests and runs in a few seconds. It uses an
in-memory database and never calls the network. You can run the same tests
with pytest or with Django's test runner.

### With pytest

```bash
pytest                                   # all tests
pytest tests/domain                      # one folder
pytest tests/domain/test_pricing.py      # one file
pytest tests/domain/test_pricing.py::PricingTests                        # one class
pytest tests/domain/test_pricing.py::PricingTests::test_value_of_a_task  # one test
pytest -k billing                        # tests whose name contains "billing"
pytest -x                                # stop at the first failure
pytest --cov                             # all tests, with coverage
```

pytest finds the Django settings through `pytest.ini` (`pytest-django` plugin,
`DJANGO_SETTINGS_MODULE = src.taskpulse.settings`).

### With Django's test runner

```bash
python manage.py test                               # all tests
python manage.py test tests.domain.test_pricing     # one module (dotted path)
coverage run manage.py test && coverage report   # with coverage
```

### Coverage

Coverage must stay at **100%** of lines and branches. The settings are in
`.coveragerc`, which both commands above read:

- Only `src/` is measured. Migrations (`src/migrations/`) are left out: they
  are generated and run once per database.
- The report lists only the files with lines or branches not run.
- The run **fails** if coverage is below 100%, so add a test with any new
  code. Check coverage on the full suite: a run of one folder or file
  covers only part of the code and will always fail the check.

### Writing tests

- **Test behaviour, not configuration.** A test should fail when something
  is broken, not whenever a line changes. Don't assert field types, labels,
  placeholders or admin column lists; test what they do (for example, the
  admin test renders the task list).
- **Test each rule once, where it lives.** Rules are tested in
  `tests/domain/` (often as a table: one test, many cases with `subTest`).
  Models, services and views get a few tests that show they use the rule.
- `tests/` mirrors `src/`. For example, `tests/domain/test_pricing.py` tests
  `src/domain/pricing.py`. A few project-wide checks sit at the top of
  `tests/`: architecture, migrations, templates (CSRF tokens), admin.
- Build data with the helpers in `tests/factories.py` (`create_project()`,
  `create_task()`, `build_task()`) and `tests/payloads.py` (form data). They
  fill in valid defaults, so a test only sets the values it is about.
- Use `SimpleTestCase` when the test doesn't need the database, and
  `TestCase` when it does.
- Never call the network. Pass a fake instead: the exchange-rate provider
  and the HTTP opener are both injectable. View tests patch
  `src.views.billing.default_provider`.
- When a rule depends on today's date, pin it:
  `mock.patch("src.models.timezone.localdate", return_value=date(2026, 11, 20))`.
- Make sure a new test can fail: break the code for a moment and check that
  the test goes red.

## Project structure

```
task-pulse/
├── manage.py
├── pytest.ini              # pytest settings
├── requirements.txt        # to run the app
├── requirements-dev.txt    # + test tools
├── src/                    # all the code (the Django app)
│   ├── taskpulse/          # project settings, root URLs, WSGI
│   ├── domain/             # business rules: pricing, Término rule, time, money,
│   │                       #   periods, statistics, chart geometry
│   ├── models.py           # Project, Task, Payment
│   ├── integrations/       # exchange-rate API, CSV files (import, payments export)
│   ├── services/           # use cases: billing, statistics, pay, export, import a file
│   ├── forms/              # one module per feature
│   ├── views/              # one module per feature
│   ├── templates/          # pages (base.html has the sidebar and the language switch)
│   ├── locale/en/          # the English translation (django.po, compiled to .mo)
│   ├── templatetags/       # |decimal_hours, |usd, |brl …
│   └── migrations/
└── tests/                  # mirrors src/
```

Each module has one responsibility, and the layers only depend downwards:

```
domain  ←  models  ←  integrations  ←  services  ←  forms  ←  views
```

- **domain** holds the rules as plain Python, with no database or HTTP, so
  they are simple to test.
- **services** combine the layers below. Forms only validate input, and views
  only turn requests into service calls and results into pages.
- The billing page depends on an `ExchangeRateProvider` interface, not on
  AwesomeAPI directly. Another source is a new class, and tests pass a fake
  one.
- `tests/test_architecture.py` fails if a module imports from a layer
  above it.

## Configuration

- The settings module is `src.taskpulse.settings`. In production, run
  `src.taskpulse.wsgi:application` from the project root, for example with
  `gunicorn src.taskpulse.wsgi:application`.
- The included settings are for **development only**: `DEBUG = True`, a
  hard-coded `SECRET_KEY`, and SQLite in `test.sqlite3` at the project root.
- Exchange-rate settings, all optional: `EXCHANGE_RATE_API_URL`,
  `EXCHANGE_RATE_TIMEOUT` (seconds, default 5) and
  `EXCHANGE_RATE_CACHE_SECONDS` (default 600).
- The Django app is the `src` package, with the label `tasks`. Database tables
  are therefore named `tasks_project` and `tasks_task`, and URL names
  `tasks:…`.

## Upgrading an existing database

Back up `test.sqlite3`, then run `python manage.py migrate`. Migrations 0003
and 0004 **cannot be undone**. What each migration changes:

| Migration | Change |
|-----------|--------|
| 0003 | Removes the `Repository` model; its URL and description are copied to each project. Renames task `nickname` to `name`. **Deletes** task `language` and the old `external_id`. |
| 0004 | Removes task `date`; it is first copied to the start date when that is empty. |
| 0005 | Stores time in minutes instead of decimal hours (`2.50` → 150 min). |
| 0006 | Adds the task's external id (unique per project). |
| 0007 | Adds payments. Existing tasks start unpaid. |
| 0008 | Adds companies. Existing projects start without one. |

## Known limitations

- The exchange-rate client was tested against AwesomeAPI's documented
  response format (with fakes, and with a local test server), never against
  the live API.
- The script that locks Término while a task is DOING has no browser test.
  The server enforces the same rule, and that part is tested.
- The script that opens the **Pagar** dialog has no browser test either.
  Without JavaScript the dialog can't be opened. Registering the payment is
  tested on the server.
- The phone layout (screens up to 720px wide, in `base.html`) was checked by
  hand in Chromium at 320–414px; there is no browser test for it, nor for
  the script that opens the sidebar from the ☰ button. On phones the
  billing and payments tables show one card per row, and the CSS labels
  their cells by column position: update it when a column changes.
- The billing page's field help is a tooltip, and touch screens don't show
  tooltips, so on a phone the help is only read by screen readers.
- A task's time total above 9999:59 is shown correctly, but can't be saved
  from the edit page, because the input allows at most 4 hour digits.

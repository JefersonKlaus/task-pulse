# Task Pulse

A Django app to plan and log work on software projects. Each project is a git
repository with tasks (goals, how to validate them, dates, time spent and
status). Tasks can be imported from a CSV file, and a dashboard shows the
hours and the earnings of a period in US dollars and Brazilian reais.

The interface is in Brazilian Portuguese.

- [Quick start](#quick-start)
- [Using the app](#using-the-app)
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

Open <http://127.0.0.1:8000/>. The sidebar links to every page.

`requirements.txt` has only what the app needs to run (Django), and
`requirements-dev.txt` adds the test tools.

## Using the app

| Page               | URL                      |
|--------------------|--------------------------|
| Dashboard (Painel) | `/painel/`               |
| Projects           | `/`                      |
| New project        | `/projetos/novo/`        |
| Project and tasks  | `/projetos/<id>/`        |
| Edit project       | `/projetos/<id>/editar/` |
| Edit task          | `/tarefas/<id>/editar/`  |
| Import tasks       | `/importar/`             |
| Admin              | `/admin/`                |

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

On **Importar tarefas**, pick an existing project, or leave **+ Criar novo
projeto** selected and enter its git URL. The file has one task per line:

```
date;id;time;desc;status
16/11/2026;TP-101;3,8;Tela de login;DONE
17/11/2026;TP-102;1,5;API de tarefas;DOING
```

| Column   | Meaning                                                              |
|----------|----------------------------------------------------------------------|
| `date`   | `dd/mm/aaaa` or `aaaa-mm-dd`. The start date, and also the finish date unless the status is DOING |
| `id`     | The task's id in the other system. Required and unique in the file  |
| `time`   | Hours: `3,8`, `3.8` or `3:48` (all 3h48). Blank means 0             |
| `desc`   | The task name                                                        |
| `status` | `DOING`, `REVIEW`, `DONE` or `REJECTED`, in any case. Blank means DOING |

- The separator can be `;`, `,` or tab. The file can be UTF-8 or Excel's
  Windows-1252, up to 2 MB. Header names may be in any order and case.
- **All or nothing**: if any line is invalid, nothing is imported, and every
  problem is listed with its line number.
- A line whose `id` already exists in the project is **skipped**, so
  importing the same file again never changes existing tasks.

### Dashboard

On **Painel**, choose a period, the statuses to include and, optionally, the
rates in US dollars:

- A task belongs to the period of its start date. Only the checked statuses
  are listed and calculated; if none is checked, all are.
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
  `/painel/?inicio=2026-11-01&fim=2026-11-30&status=DONE&valor_hora=90`.

## Running the tests

The suite has about 140 tests and runs in a few seconds. It uses an
in-memory database and never calls the network. You can run the same tests
with pytest or with Django's test runner.

### With pytest

```bash
pytest                                   # all tests
pytest tests/domain                      # one folder
pytest tests/domain/test_pricing.py      # one file
pytest tests/domain/test_pricing.py::PricingTests                        # one class
pytest tests/domain/test_pricing.py::PricingTests::test_value_of_a_task  # one test
pytest -k dashboard                      # tests whose name contains "dashboard"
pytest -x                                # stop at the first failure
pytest --cov=src --cov-report=term-missing   # with coverage
```

pytest finds the Django settings through `pytest.ini` (`pytest-django` plugin,
`DJANGO_SETTINGS_MODULE = src.taskpulse.settings`).

### With Django's test runner

```bash
python manage.py test                               # all tests
python manage.py test tests.domain.test_pricing     # one module (dotted path)
coverage run --source=src manage.py test && coverage report -m
```

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
  `src.views.dashboard.default_provider`.
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
│   ├── domain/             # business rules: pricing, Término rule, time, money
│   ├── models.py           # Project, Task
│   ├── integrations/       # exchange-rate API, CSV file format
│   ├── services/           # use cases: build the dashboard, import a file
│   ├── forms/              # one module per feature
│   ├── views/              # one module per feature
│   ├── templates/          # pages (base.html has the sidebar)
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
- The dashboard depends on an `ExchangeRateProvider` interface, not on
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

## Known limitations

- The exchange-rate client was tested against AwesomeAPI's documented
  response format (with fakes, and with a local test server), never against
  the live API.
- The script that locks Término while a task is DOING has no browser test.
  The server enforces the same rule, and that part is tested.
- A task's time total above 9999:59 is shown correctly, but can't be saved
  from the edit page, because the input allows at most 4 hour digits.

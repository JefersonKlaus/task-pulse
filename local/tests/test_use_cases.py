"""The use cases against both repositories (memory and DynamoDB format): companies, projects, rules,
tasks, billing and payments."""
import pytest

from add_task_time.use_case import add_task_time
from create_company.use_case import create_company
from create_payment.use_case import create_payment
from create_project.use_case import create_project
from create_rule.use_case import create_rule
from create_task.use_case import create_task
from delete_company.use_case import delete_company
from delete_payment.use_case import delete_payment
from delete_project.use_case import delete_project
from delete_rule.use_case import delete_rule
from delete_task.use_case import delete_task
from get_billing.use_case import get_billing
from list_companies.use_case import list_companies
from list_payments.use_case import list_payments
from list_projects.use_case import list_projects
from list_tasks.use_case import list_tasks
from pulse_core.domain.errors import BusinessError, NotFound, ValidationError
from update_company.use_case import update_company
from update_rule.use_case import update_rule
from update_task.use_case import update_task

from conftest import OTHER, OWNER, fixed, hourly

NOV = {"from": "2026-11-01", "to": "2026-11-30"}


@pytest.fixture
def project(deps, clock):
    company = create_company(deps, OWNER, {"name": "Alignerr"})
    return create_project(deps, OWNER, {"company_id": company["id"], "name": "Review", "currency": "USD",
                                        "rule": hourly(flat_cents=10000)})


def done(deps, project, name, minutes=300, finished_at="2026-11-10T17:00", status="APPROVED", **extra):
    return create_task(deps, OWNER, project["id"], {"name": name, "started_at": "2026-11-01T09:00",
                                                     "status": status, "minutes": minutes,
                                                     "finished_at": finished_at, **extra})


# ------------------------------------------------------------------ companies and projects
def test_company_names_are_unique_ignoring_case(deps):
    create_company(deps, OWNER, {"name": "Etho"})
    with pytest.raises(ValidationError, match="Já existe"):
        create_company(deps, OWNER, {"name": "etho"})
    create_company(deps, OTHER, {"name": "Etho"})          # another user: their own data


def test_company_with_projects_is_not_deleted(deps, project):
    with pytest.raises(BusinessError, match="projetos"):
        delete_company(deps, OWNER, project["company_id"])
    delete_project(deps, OWNER, project["id"])
    delete_company(deps, OWNER, project["company_id"])
    assert list_companies(deps, OWNER) == []


def test_users_never_see_each_others_data(deps, project):
    assert list_projects(deps, OTHER, {}) == []
    with pytest.raises(NotFound):
        create_task(deps, OTHER, project["id"], {"name": "x"})
    with pytest.raises(NotFound):
        update_company(deps, OTHER, project["company_id"], {"name": "x"})


def test_project_needs_an_existing_company(deps):
    with pytest.raises(NotFound):
        create_project(deps, OWNER, {"company_id": "nope", "name": "P"})


def test_projects_filtered_by_company(deps, project, clock):
    other = create_company(deps, OWNER, {"name": "Etho"})
    create_project(deps, OWNER, {"company_id": other["id"], "name": "Portal"})
    assert [p["name"] for p in list_projects(deps, OWNER, {"company_id": other["id"]})] == ["Portal"]
    assert len(list_projects(deps, OWNER, {})) == 2


# ------------------------------------------------------------------ rules by date
def test_new_rule_closes_the_open_one_and_keeps_yesterdays_value(deps, project, clock):
    yesterday = done(deps, project, "Ontem", finished_at="2026-11-19T18:00")
    view = create_rule(deps, OWNER, project["id"], hourly(starts_at="2026-11-20T09:00", hourly_cents=12000))
    old, new = view["rules"]
    assert old["ends_at"] == "2026-11-20T09:00" and new["ends_at"] is None
    today = done(deps, project, "Hoje", finished_at="2026-11-20T10:00", status="DONE")
    rows = {t["name"]: t for t in list_tasks(deps, OWNER, {"state": "finished", **NOV})["tasks"]}
    assert rows["Ontem"]["value_cents"] == 46000 and rows["Ontem"]["rule_id"] == old["id"]
    assert rows["Hoje"]["value_cents"] == 60000 and rows["Hoje"]["rule_id"] == new["id"]
    assert yesterday["id"] != today["id"]


def test_rules_cannot_overlap(deps, project):
    create_rule(deps, OWNER, project["id"], hourly(starts_at="2026-12-01T00:00", ends_at="2026-12-10T00:00"))
    with pytest.raises(ValidationError, match="sobrepor"):
        create_rule(deps, OWNER, project["id"], hourly(starts_at="2026-12-05T00:00", ends_at="2026-12-20T00:00"))


def test_rule_with_concluded_tasks_keeps_its_values(deps, project):
    rule = project["rules"][0]
    done(deps, project, "A", finished_at="2026-11-10T17:00")
    with pytest.raises(ValidationError, match="nova regra"):
        update_rule(deps, OWNER, project["id"], rule["id"], {**rule, "hourly_cents": 1})
    with pytest.raises(ValidationError, match="depois disso"):
        update_rule(deps, OWNER, project["id"], rule["id"], {**rule, "ends_at": "2026-11-10T12:00"})
    view = update_rule(deps, OWNER, project["id"], rule["id"], {**rule, "ends_at": "2026-11-15T00:00"})
    assert view["rules"][0]["ends_at"] == "2026-11-15T00:00"
    with pytest.raises(BusinessError, match="não pode ser excluída"):
        delete_rule(deps, OWNER, project["id"], rule["id"])


def test_rule_without_tasks_changes_freely(deps, project):
    rule = project["rules"][0]
    view = update_rule(deps, OWNER, project["id"], rule["id"], fixed())
    assert view["rules"][0]["kind"] == "fixed"
    assert delete_rule(deps, OWNER, project["id"], rule["id"])["rules"] == []


# ------------------------------------------------------------------ tasks
def test_new_task_starts_doing_now(deps, project, clock):
    task = create_task(deps, OWNER, project["id"], {"name": "Nova", "external_id": "CR-1",
                                                     "repository": "acme/api", "description": "d"})
    assert (task["status"], task["started_at"], task["finished_at"], task["minutes"]) == \
        ("DOING", clock.now, None, 0)


def test_task_created_concluded_needs_time_and_finish(deps, project):
    with pytest.raises(ValidationError, match="tempo"):
        create_task(deps, OWNER, project["id"], {"name": "x", "status": "DONE", "finished_at": "2026-11-10T10:00"})
    with pytest.raises(ValidationError, match="terminou"):
        create_task(deps, OWNER, project["id"], {"name": "x", "status": "DONE", "minutes": 30})


def test_external_id_is_unique_per_project(deps, project):
    create_task(deps, OWNER, project["id"], {"name": "a", "external_id": "CR-1"})
    with pytest.raises(ValidationError, match="ID externo"):
        create_task(deps, OWNER, project["id"], {"name": "b", "external_id": "cr-1"})
    create_task(deps, OWNER, project["id"], {"name": "c"})
    create_task(deps, OWNER, project["id"], {"name": "d"})       # blank: any number of them


def test_adding_time_then_finishing_takes_this_moment(deps, project, clock):
    task = create_task(deps, OWNER, project["id"], {"name": "x", "started_at": "2026-11-18T09:00"})
    task = add_task_time(deps, OWNER, project["id"], task["id"], {"minutes": 120})
    clock.now = "2026-11-21T16:30"
    task = add_task_time(deps, OWNER, project["id"], task["id"], {"minutes": 45, "finish": True})
    assert (task["minutes"], task["status"], task["finished_at"]) == (165, "DONE", "2026-11-21T16:30")
    assert [e["minutes"] for e in task["time_log"]] == [120, 45]
    with pytest.raises(ValidationError):
        add_task_time(deps, OWNER, project["id"], task["id"], {"minutes": 0})


def test_approving_and_reopening(deps, project, clock):
    task = done(deps, project, "x", status="DONE")
    task = update_task(deps, OWNER, project["id"], task["id"], {"status": "APPROVED"})
    assert task["finished_at"] == "2026-11-10T17:00" and task["value_cents"] == 46000
    task = update_task(deps, OWNER, project["id"], task["id"], {"status": "DOING"})
    assert task["finished_at"] is None and task["value_cents"] == 0


def test_open_tasks_by_period_company_and_project(deps, project, clock):
    create_task(deps, OWNER, project["id"], {"name": "Outubro", "started_at": "2026-10-20T09:00"})
    create_task(deps, OWNER, project["id"], {"name": "Dezembro", "started_at": "2026-12-02T09:00"})
    done(deps, project, "Feita")
    week = list_tasks(deps, OWNER, {"from": "2026-11-16", "to": "2026-11-22"})
    assert [t["name"] for t in week["tasks"]] == ["Outubro"]      # still open, started before the week
    assert list_tasks(deps, OWNER, {"company_id": "other", **NOV})["tasks"] == []
    assert len(list_tasks(deps, OWNER, {"state": "all", "project_id": project["id"]})["tasks"]) == 3


# ------------------------------------------------------------------ billing and payments
def test_billing_marks_not_paid_and_compares_received(deps, project):
    create_rule(deps, OWNER, project["id"], hourly(starts_at="2026-11-12T00:00", hourly_cents=6000,
                                                   bonus_tiers=[{"min_tasks": 2, "bonus_cents": 2000}]))
    a = done(deps, project, "A", finished_at="2026-11-10T17:00")                 # old rule: 460
    b = done(deps, project, "B", minutes=120, finished_at="2026-11-13T17:00")    # new: 60 + 60 = 120
    c = done(deps, project, "C", minutes=60, finished_at="2026-11-14T17:00", status="DONE")   # 60
    report = get_billing(deps, OWNER, project["id"], NOV)
    assert [t["value_cents"] for t in report["tasks"]] == [46000, 12000, 6000]
    assert report["bonus"]["due_cents"] == 2000
    assert report["totals"]["to_receive_cents"] == 66000

    report = create_payment(deps, OWNER, project["id"], {
        "period_start": NOV["from"], "period_end": NOV["to"], "received_cents": 50000,
        "received_on": "2026-12-05", "not_paid_task_ids": [c["id"]]})
    rows = {t["name"]: t for t in report["tasks"]}
    assert (rows["A"]["billing"], rows["C"]["billing"], rows["C"]["lost_cents"]) == ("paid", "not_paid", 6000)
    totals = report["totals"]
    assert (totals["paid_tasks"], totals["not_paid_tasks"], totals["open_tasks"]) == (2, 1, 0)
    assert totals["expected_cents"] == 60000                    # 460 + 120 + bonus 20
    assert (totals["received_cents"], totals["difference_cents"]) == (50000, -10000)
    assert totals["not_paid_value_cents"] == 6000 and totals["to_receive_cents"] == 0

    # paid tasks are frozen: a rule change or an edit can't change what was paid
    with pytest.raises(ValidationError, match="faturada"):
        update_task(deps, OWNER, project["id"], a["id"], {"minutes": 1})
    with pytest.raises(BusinessError, match="faturada"):
        delete_task(deps, OWNER, project["id"], b["id"])
    payments = list_payments(deps, OWNER, {"company_id": project["company_id"]})
    assert payments["totals"] == {"expected_cents": 60000, "received_cents": 50000, "difference_cents": -10000,
                                  "not_paid_cents": 6000}

    delete_payment(deps, OWNER, project["id"], payments["payments"][0]["id"])
    report = get_billing(deps, OWNER, project["id"], NOV)
    assert report["totals"]["open_tasks"] == 3 and report["payments"] == []


def test_payment_needs_open_tasks(deps, project):
    with pytest.raises(ValidationError, match="Nenhuma tarefa"):
        create_payment(deps, OWNER, project["id"], {"period_start": NOV["from"], "period_end": NOV["to"],
                                                    "received_cents": 1})


def test_a_later_payment_in_the_period_only_takes_the_new_tasks(deps, project):
    done(deps, project, "A")
    create_payment(deps, OWNER, project["id"], {"period_start": NOV["from"], "period_end": NOV["to"],
                                                "received_cents": 46000})
    done(deps, project, "B", minutes=60, finished_at="2026-11-25T10:00")
    report = create_payment(deps, OWNER, project["id"], {"period_start": NOV["from"], "period_end": NOV["to"],
                                                         "received_cents": 10000})
    assert [p["expected_cents"] for p in report["payments"]] in ([10000, 46000], [46000, 10000])
    assert report["totals"]["difference_cents"] == 0


def test_period_is_validated(deps, project):
    with pytest.raises(ValidationError, match="depois do início"):
        get_billing(deps, OWNER, project["id"], {"from": "2026-11-30", "to": "2026-11-01"})

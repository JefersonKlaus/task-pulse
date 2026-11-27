"""The well-known companies (the same for everyone, never edited) and a project's many deadlines (on a day,
weekly or monthly)."""
from dataclasses import replace

import pytest

from create_company.use_case import create_company
from create_project.use_case import create_project
from delete_company.use_case import delete_company
from get_project.use_case import get_project
from list_companies.use_case import list_companies
from list_known_companies.use_case import list_known_companies
from list_projects.use_case import list_projects
from update_company.use_case import update_company
from update_project.use_case import update_project
from pulse_core.domain.catalog import KNOWN_COMPANIES
from pulse_core.domain.errors import BusinessError, ValidationError
from pulse_core.domain.models import Company, Deadline, Project

from conftest import OTHER, OWNER


# ------------------------------------------------------------------ well-known companies
def test_a_well_known_company_is_the_same_for_everyone(deps):
    mine = create_company(deps, OWNER, {"known_id": "alignerr"})
    theirs = create_company(deps, OTHER, {"name": "  alignerr "})      # typed: the same company
    assert mine == theirs == {"id": "alignerr", "name": "Alignerr", "notes": "Plataforma da Labelbox.",
                              "known": True}
    p1 = create_project(deps, OWNER, {"company_id": "alignerr", "name": "A"})
    p2 = create_project(deps, OTHER, {"company_id": "alignerr", "name": "B"})
    assert p1["company_id"] == p2["company_id"] == "alignerr"           # what reports group by
    assert p1["company_known"] is True


def test_the_catalog_lists_every_well_known_company(deps):
    known = list_known_companies(deps, OWNER)
    assert len(known) == len(KNOWN_COMPANIES) and all(c["known"] for c in known)
    assert len({c["id"] for c in known}) == len(known)


def test_a_well_known_company_is_not_edited_but_can_leave_the_list(deps):
    create_company(deps, OWNER, {"known_id": "outlier"})
    with pytest.raises(BusinessError, match="não pode ser editada"):
        update_company(deps, OWNER, "outlier", {"name": "Outlier (Scale)"})
    with pytest.raises(ValidationError, match="Já existe"):
        create_company(deps, OWNER, {"known_id": "outlier"})
    with pytest.raises(ValidationError, match="não encontrada"):
        create_company(deps, OWNER, {"known_id": "nope"})
    delete_company(deps, OWNER, "outlier")
    assert list_companies(deps, OWNER) == []


def test_an_own_company_cant_take_a_well_known_name(deps):
    own = create_company(deps, OWNER, {"name": "Etho"})
    assert own["known"] is False
    with pytest.raises(ValidationError, match="empresa padrão"):
        update_company(deps, OWNER, own["id"], {"name": "Mercor"})


def test_a_company_registered_by_hand_with_a_well_known_name_is_adopted(deps, repo):
    """Before the catalog, Alignerr was registered by hand: listing the companies moves its projects to
    the shared Alignerr and removes the old record."""
    repo.save_company(OWNER, Company("old-id", "ALIGNERR", "minhas notas"))
    repo.save_project(OWNER, Project("p1", "old-id", "live-compare", "USD"))
    companies = list_companies(deps, OWNER)
    assert [(c["id"], c["name"], c["known"], c["projects"]) for c in companies] == [("alignerr", "Alignerr", True, 1)]
    assert repo.get_company(OWNER, "old-id") is None
    assert repo.get_project(OWNER, "p1").company_id == "alignerr"
    assert list_companies(deps, OWNER) == companies                    # nothing left to adopt


def test_a_well_known_company_shows_the_catalogs_name(deps, repo):
    repo.save_company(OWNER, Company("mindrift", "old name", "", known=True))
    assert list_companies(deps, OWNER)[0]["name"] == "Mindrift"


# ------------------------------------------------------------------ deadlines
@pytest.mark.parametrize("deadline, today, expected", [
    (Deadline("d", "date", on="2026-12-01"), "2026-11-27", "2026-12-01"),
    (Deadline("d", "date", on="2026-11-26"), "2026-11-27", None),          # passed
    (Deadline("d", "weekly", weekday=5), "2026-11-27", "2026-11-27"),       # a Friday: today
    (Deadline("d", "weekly", weekday=1), "2026-11-27", "2026-11-30"),       # next Monday
    (Deadline("d", "monthly", month_day=30), "2026-11-27", "2026-11-30"),
    (Deadline("d", "monthly", month_day=10), "2026-11-27", "2026-12-10"),   # next month
    (Deadline("d", "monthly", month_day=31), "2027-02-01", "2027-02-28"),   # a short month: its last day
    (Deadline("d", "monthly", month_day=5), "2026-12-20", "2027-01-05"),    # over the year
])
def test_the_next_day_of_a_deadline(deadline, today, expected):
    assert deadline.next_on(today) == expected


def test_a_project_has_many_deadlines_and_the_nearest_is_shown(deps, clock):
    clock.now = "2026-11-27T10:00"
    create_company(deps, OWNER, {"name": "Etho"})
    company_id = list_companies(deps, OWNER)[0]["id"]
    project = create_project(deps, OWNER, {"company_id": company_id, "name": "Portal", "deadlines": [
        {"kind": "monthly", "label": "Mês", "month_day": 30},
        {"kind": "weekly", "label": "Semana", "weekday": 1},
        {"kind": "date", "label": "Final", "on": "2027-01-15"},
    ]})
    assert [(d["label"], d["next_on"]) for d in project["deadlines"]] == [
        ("Mês", "2026-11-30"), ("Semana", "2026-11-30"), ("Final", "2027-01-15")]
    assert project["next_deadline"]["next_on"] == "2026-11-30"
    kept = project["deadlines"][2]
    edited = update_project(deps, OWNER, project["id"], {"company_id": company_id, "name": "Portal",
                                                         "deadlines": [kept]})
    assert [d["id"] for d in edited["deadlines"]] == [kept["id"]]       # the id stays
    assert get_project(deps, OWNER, project["id"])["next_deadline"]["label"] == "Final"
    assert list_projects(deps, OWNER, {})[0]["next_deadline"]["label"] == "Final"


@pytest.mark.parametrize("deadline, message", [
    ({"kind": "yearly"}, "escolha data"),
    ({"kind": "weekly", "weekday": 8}, "dia da semana"),
    ({"kind": "monthly", "month_day": 0}, "dia do mês"),
    ({"kind": "date", "on": "2026-02-30"}, "Data do prazo"),
    ("x", "item inválido"),
])
def test_bad_deadlines_are_refused(deps, deadline, message):
    company = create_company(deps, OWNER, {"name": "Etho"})
    with pytest.raises(ValidationError, match=message):
        create_project(deps, OWNER, {"company_id": company["id"], "name": "P", "deadlines": [deadline]})


def test_a_project_saved_with_one_deadline_reads_as_a_list(repo):
    project = Project.from_dict({"id": "p", "company_id": "c", "name": "P", "deadline": "2026-12-20"})
    assert project.deadlines == (Deadline("deadline", "date", "", on="2026-12-20"),)
    assert Project.from_input({"company_id": "c", "name": "P", "deadline": "2026-12-20"}).deadlines[0].on == "2026-12-20"
    repo.save_project(OWNER, replace(project, deadlines=project.deadlines + (Deadline("w", "weekly", "S", weekday=3),)))
    assert repo.get_project(OWNER, "p").deadlines[1] == Deadline("w", "weekly", "S", weekday=3)

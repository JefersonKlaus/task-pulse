"""Form / HTTP POST payloads shared by form and view tests."""

PROJECT_URL = "https://github.com/acme/portal.git"


def project_form_data(**overrides):
    data = {"url": PROJECT_URL, "name": "Novo projeto", "description": ""}
    data.update(overrides)
    return data


def task_create_data(**overrides):
    """Payload of the "Nova tarefa" form on the project page."""
    data = {
        "name": "Nova tarefa",
        "description": "",
        "acceptance_criteria": "",
    }
    data.update(overrides)
    return data


def task_update_data(**overrides):
    """Payload of the "edit task" form (every field).

    The default status is REVIEW so the finish date is accepted; pass
    ``status="DOING"`` to test the locked field. Time is typed as H:MM.
    """
    data = {
        "name": "Tarefa editada",
        "description": "",
        "acceptance_criteria": "",
        "started_on": "2026-11-16",
        "status": "REVIEW",
        "finished_on": "2026-11-18",
        "minutes_spent": "2:15",
        "add_time": "",
    }
    data.update(overrides)
    return data


def without(data, *keys):
    """Return a copy of ``data`` without ``keys`` (simulates a missing field)."""
    return {key: value for key, value in data.items() if key not in keys}

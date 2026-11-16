"""Which finish date ("Término") a task has after a change.

* DOING: the task is not finished, so there is no finish date.
* Moving into REVIEW or DONE: the finish date is today, unless the user
  typed one in the same change. Moving between REVIEW and DONE keeps it.
* REJECTED: whatever the user entered is kept.
"""

from .task_status import FINISHED_STATUSES, TaskStatus


def resolve_finished_on(
    *, status, finished_on, previous_status, previous_finished_on, today
):
    """The finish date to store.

    ``previous_*`` describe the task as stored before the change (both
    ``None`` for a new task); ``finished_on`` is the value being saved.
    """
    if status == TaskStatus.DOING:
        return None
    if status not in FINISHED_STATUSES or previous_status in FINISHED_STATUSES:
        return finished_on
    if finished_on == previous_finished_on:  # not typed by the user
        return today
    return finished_on

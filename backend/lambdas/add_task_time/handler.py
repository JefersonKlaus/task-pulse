"""Inbound adapter of this Lambda: POST /projects/{id}/tasks/{task_id}/time -> use case. `handle(event, deps)` is what the local
server and the tests call; `lambda_handler` is what AWS calls, plugged into DynamoDB."""
from pulse_core.adapters.api_gateway import endpoint
from pulse_core.adapters.aws import aws_dependencies

from .use_case import add_task_time

handle = endpoint(lambda deps, r: add_task_time(deps, r.owner, r.id, r.path['task_id'], r.body))


def lambda_handler(event, context):
    return handle(event, aws_dependencies())

"""Inbound adapter of this Lambda: GET /projects/{id} -> use case. `handle(event, deps)` is what the local
server and the tests call; `lambda_handler` is what AWS calls, plugged into DynamoDB."""
from pulse_core.adapters.api_gateway import endpoint
from pulse_core.adapters.aws import aws_dependencies

from .use_case import get_project

handle = endpoint(lambda deps, r: get_project(deps, r.owner, r.id))


def lambda_handler(event, context):
    return handle(event, aws_dependencies())

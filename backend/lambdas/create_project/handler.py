"""Inbound adapter of this Lambda: POST /projects -> use case. `handle(event, deps)` is what the local
server and the tests call; `lambda_handler` is what AWS calls, plugged into DynamoDB."""
from pulse_core.adapters.api_gateway import endpoint
from pulse_core.adapters.aws import aws_dependencies

from .use_case import create_project

handle = endpoint(lambda deps, r: create_project(deps, r.owner, r.body), status=201)


def lambda_handler(event, context):
    return handle(event, aws_dependencies())

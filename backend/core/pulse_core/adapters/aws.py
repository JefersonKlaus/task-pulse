"""Composition root in AWS: plugs the ports into DynamoDB."""
from __future__ import annotations

import os
from typing import Optional

from ..ports import Dependencies
from .dynamo_repository import DynamoRepository

_dependencies: Optional[Dependencies] = None


def aws_dependencies() -> Dependencies:
    global _dependencies
    if _dependencies is None:       # created once per execution environment and reused
        import boto3                # already present in Lambda; imported here so tests don't require it
        _dependencies = Dependencies(DynamoRepository(boto3.client("dynamodb"), os.environ["TABLE_NAME"]))
    return _dependencies

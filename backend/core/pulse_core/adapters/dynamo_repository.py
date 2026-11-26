"""DynamoDB repository, single table.

PK = OWNER#<owner>   SK = COMPANY#<company id>
                     | PROJECT#<project id>            (with its pricing rules inside)
                     | TASK#<project id>#<task id>
                     | PAY#<project id>#<payment id>

The item stores the whole object as JSON in the `data` attribute. One project's tasks are one query
(begins_with TASK#<project id>#); every project's tasks, another (begins_with TASK#). Payments work the
same way with PAY#. The `owner` always comes from the login token, never from what the browser sends:
that is what keeps each user's data apart.
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from ..domain.models import Company, Payment, Project, Task

OWNER_PREFIX = "OWNER#"
COMPANY_PREFIX, PROJECT_PREFIX, TASK_PREFIX, PAYMENT_PREFIX = "COMPANY#", "PROJECT#", "TASK#", "PAY#"
DATA_ATTRIBUTE = "data"
BATCH_SIZE = 25                 # the most BatchWriteItem takes in one call
BATCH_ATTEMPTS = 8


class DynamoRepository:
    def __init__(self, client: Any, table: str) -> None:
        self.client, self.table = client, table

    # -------------------------------------------------------------- low level
    def _key(self, owner: str, sk: str) -> dict[str, Any]:
        return {"PK": {"S": f"{OWNER_PREFIX}{owner}"}, "SK": {"S": sk}}

    def _item(self, owner: str, sk: str, obj: dict[str, Any]) -> dict[str, Any]:
        return {**self._key(owner, sk), DATA_ATTRIBUTE: {"S": json.dumps(obj, ensure_ascii=False)}}

    def _put(self, owner: str, sk: str, obj: dict[str, Any]) -> None:
        self.client.put_item(TableName=self.table, Item=self._item(owner, sk, obj))

    def _read(self, owner: str, sk: str) -> Optional[dict[str, Any]]:
        item = self.client.get_item(TableName=self.table, Key=self._key(owner, sk), ConsistentRead=True).get("Item")
        return json.loads(item[DATA_ATTRIBUTE]["S"]) if item else None

    def _delete(self, owner: str, sk: str) -> None:
        self.client.delete_item(TableName=self.table, Key=self._key(owner, sk))

    def _batch(self, requests: list[dict[str, Any]]) -> None:
        """Writes/deletes in calls of 25; what DynamoDB leaves unprocessed (throttling) is sent again."""
        for start in range(0, len(requests), BATCH_SIZE):
            pending = {self.table: requests[start:start + BATCH_SIZE]}
            for attempt in range(BATCH_ATTEMPTS):
                pending = self.client.batch_write_item(RequestItems=pending).get("UnprocessedItems") or {}
                if not pending:
                    break
                time.sleep(0.05 * 2 ** attempt)
            else:
                raise RuntimeError("DynamoDB did not accept every item of the batch")

    def _query_prefix(self, owner: str, prefix: str) -> list[dict[str, Any]]:
        items, start_key = [], None
        while True:
            request = {"TableName": self.table, "ConsistentRead": True,
                       "KeyConditionExpression": "PK = :pk AND begins_with(SK, :p)",
                       "ExpressionAttributeValues": {":pk": {"S": f"{OWNER_PREFIX}{owner}"}, ":p": {"S": prefix}}}
            if start_key:
                request["ExclusiveStartKey"] = start_key
            response = self.client.query(**request)
            items += [json.loads(i[DATA_ATTRIBUTE]["S"]) for i in response.get("Items", [])]
            start_key = response.get("LastEvaluatedKey")
            if not start_key:
                return items

    # -------------------------------------------------------------- companies
    def list_companies(self, owner: str) -> list[Company]:
        return [Company.from_dict(d) for d in self._query_prefix(owner, COMPANY_PREFIX)]

    def get_company(self, owner: str, id: str) -> Optional[Company]:
        data = self._read(owner, f"{COMPANY_PREFIX}{id}")
        return Company.from_dict(data) if data else None

    def save_company(self, owner: str, company: Company) -> None:
        self._put(owner, f"{COMPANY_PREFIX}{company.id}", company.to_dict())

    def delete_company(self, owner: str, id: str) -> None:
        self._delete(owner, f"{COMPANY_PREFIX}{id}")

    # -------------------------------------------------------------- projects
    def list_projects(self, owner: str) -> list[Project]:
        return [Project.from_dict(d) for d in self._query_prefix(owner, PROJECT_PREFIX)]

    def get_project(self, owner: str, id: str) -> Optional[Project]:
        data = self._read(owner, f"{PROJECT_PREFIX}{id}")
        return Project.from_dict(data) if data else None

    def save_project(self, owner: str, project: Project) -> None:
        self._put(owner, f"{PROJECT_PREFIX}{project.id}", project.to_dict())

    def delete_project(self, owner: str, id: str) -> None:
        self._delete(owner, f"{PROJECT_PREFIX}{id}")

    # -------------------------------------------------------------- tasks
    def list_tasks(self, owner: str, project_id: Optional[str] = None) -> list[Task]:
        prefix = f"{TASK_PREFIX}{project_id}#" if project_id else TASK_PREFIX
        return [Task.from_dict(d) for d in self._query_prefix(owner, prefix)]

    def get_task(self, owner: str, project_id: str, id: str) -> Optional[Task]:
        data = self._read(owner, f"{TASK_PREFIX}{project_id}#{id}")
        return Task.from_dict(data) if data else None

    def save_tasks(self, owner: str, tasks: list[Task]) -> None:
        if len(tasks) == 1:
            self._put(owner, f"{TASK_PREFIX}{tasks[0].project_id}#{tasks[0].id}", tasks[0].to_dict())
            return
        self._batch([{"PutRequest": {"Item": self._item(owner, f"{TASK_PREFIX}{t.project_id}#{t.id}", t.to_dict())}}
                     for t in tasks])

    def delete_tasks(self, owner: str, project_id: str, ids: list[str]) -> None:
        self._batch([{"DeleteRequest": {"Key": self._key(owner, f"{TASK_PREFIX}{project_id}#{id}")}} for id in ids])

    # -------------------------------------------------------------- payments
    def list_payments(self, owner: str, project_id: Optional[str] = None) -> list[Payment]:
        prefix = f"{PAYMENT_PREFIX}{project_id}#" if project_id else PAYMENT_PREFIX
        return [Payment.from_dict(d) for d in self._query_prefix(owner, prefix)]

    def get_payment(self, owner: str, project_id: str, id: str) -> Optional[Payment]:
        data = self._read(owner, f"{PAYMENT_PREFIX}{project_id}#{id}")
        return Payment.from_dict(data) if data else None

    def save_payment(self, owner: str, payment: Payment) -> None:
        self._put(owner, f"{PAYMENT_PREFIX}{payment.project_id}#{payment.id}", payment.to_dict())

    def delete_payments(self, owner: str, project_id: str, ids: list[str]) -> None:
        self._batch([{"DeleteRequest": {"Key": self._key(owner, f"{PAYMENT_PREFIX}{project_id}#{id}")}}
                     for id in ids])

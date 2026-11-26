"""The DynamoDB repository: keys, pagination of queries and batches (with a fake client)."""
from datetime import date

from conftest import OWNER, FakeDynamo
from memory_repository import MemoryRepository
from pulse_core.adapters.dynamo_repository import DynamoRepository
from pulse_core.domain.models import Task
from pulse_core.ports import Dependencies
from seed import seed


def test_keys_are_under_the_owner():
    fake = FakeDynamo()
    repo = DynamoRepository(fake, "t")
    repo.save_tasks(OWNER, [Task("t1", "p1", "x", "2026-11-01T09:00")])
    assert list(fake.items) == [(f"OWNER#{OWNER}", "TASK#p1#t1")]


def test_batches_of_25_and_retries_unprocessed():
    fake = FakeDynamo(unprocessed=2)
    repo = DynamoRepository(fake, "t")
    repo.save_tasks(OWNER, [Task(f"t{i:02d}", "p1", "x", "2026-11-01T09:00") for i in range(30)])
    assert len(repo.list_tasks(OWNER, "p1")) == 30          # paginated query (page of 2)
    assert fake.batch_calls == 4                             # 25 + 5, and two retries
    repo.delete_tasks(OWNER, "p1", [f"t{i:02d}" for i in range(30)])
    assert repo.list_tasks(OWNER) == []


def test_demo_data_reads_back_the_same_from_both_repositories():
    memory, dynamo = Dependencies(MemoryRepository()), Dependencies(DynamoRepository(FakeDynamo(), "t"))
    for deps in (memory, dynamo):
        seed(deps, OWNER, date(2026, 11, 20))
    for kind in ("companies", "projects", "tasks", "payments"):
        def names(deps):
            items = getattr(deps.repo, f"list_{kind}")(OWNER)
            return sorted(getattr(i, "name", None) or getattr(i, "received_on") for i in items)
        assert names(memory) == names(dynamo), kind

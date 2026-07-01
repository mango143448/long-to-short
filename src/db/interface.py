from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.types import JobResult


class Repository(ABC):
    @abstractmethod
    async def save_job(self, job: JobResult) -> None:
        ...

    @abstractmethod
    async def get_job(self, url: str) -> Optional[JobResult]:
        ...

    @abstractmethod
    async def list_jobs(self, user_id: Optional[str] = None) -> list[JobResult]:
        ...

    @abstractmethod
    async def delete_job(self, url: str) -> bool:
        ...


class InMemoryRepository(Repository):
    def __init__(self):
        self._store: dict[str, JobResult] = {}

    async def save_job(self, job: JobResult) -> None:
        self._store[job.url] = job

    async def get_job(self, url: str) -> Optional[JobResult]:
        return self._store.get(url)

    async def list_jobs(self, user_id: Optional[str] = None) -> list[JobResult]:
        return list(self._store.values())

    async def delete_job(self, url: str) -> bool:
        return self._store.pop(url, None) is not None


_repo: Repository = InMemoryRepository()


def get_repository() -> Repository:
    return _repo


def set_repository(repo: Repository):
    global _repo
    _repo = repo

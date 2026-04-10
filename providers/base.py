"""Base provider interfaces."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.models import MediaCandidate
from core.url_safety import normalize_url


@dataclass
class ProviderError(Exception):
    """Provider failure with retryability classification."""

    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    def can_handle(self, url: str) -> bool: ...

    @abstractmethod
    async def resolve(self, url: str, proxy: Optional[str] = None) -> Optional[MediaCandidate]: ...


_URL_PATTERN = re.compile(
    r"^(https?://)"
    r"([A-Za-z0-9\-\.]+)"
    r"(\.[A-Za-z]{2,})"
    r"(:\d+)?"
    r"(/[^\s]*)?"
    r"$",
    re.IGNORECASE,
)


def is_valid_url(url: str) -> bool:
    return bool(_URL_PATTERN.match(normalize_url(url)))

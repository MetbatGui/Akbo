"""DDD 베이스 엔티티/도메인 이벤트 프로토콜.

- `DomainEvent`: 런타임/정적 타입 검사에 사용할 최소 프로토콜.
- `Entity`: 불변(`frozen=True`) + `slots=True` 기반의 엔티티 베이스 구현.
  - 시간 값은 모두 타임존 정보가 있는(aware) `datetime`(보통 UTC)을 요구합니다.
  - 이벤트는 내부 큐에 누적되며, `drain_events()`로 배출+초기화합니다.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Protocol, Self, runtime_checkable
from uuid import UUID, uuid4

from akbo.shared.domain.exceptions import (
    TimestampMustBeTimezoneAwareError,
    TimestampOrderError,
)


@runtime_checkable
class DomainEvent(Protocol):
    """도메인 이벤트 최소 프로토콜.

    이벤트 ID 정책(예: uuid4, uuid7 등)은 각 이벤트 구현체가 결정합니다.
    이 프로토콜을 만족하려면 `occurred_at`(aware datetime)을 제공해야 합니다.

    Attributes:
        id (UUID): 이벤트 식별자.
        occurred_at (datetime): 이벤트 발생 시각(UTC 권장, aware datetime).
    """

    id: UUID
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Entity(ABC):
    """DDD 스타일의 불변 엔티티 베이스 클래스.

    모든 엔티티는 고유 `id`와 생성/수정 시각을 가지며, 내부적으로 도메인
    이벤트를 큐에 쌓아둘 수 있습니다. 불변성을 유지하기 위해 변경 연산은
    항상 새로운 인스턴스를 반환합니다.

    Attributes:
        id (UUID): 엔티티 식별자(기본값: `uuid4()`).
        version (int): 낙관적 락/버전 관리용 카운터.
        created_at (datetime): 생성 시각(aware datetime, 보통 UTC).
        updated_at (datetime): 마지막 변경 시각(aware datetime, 보통 UTC).
        archived_at (Optional[datetime]): 보관(소프트 삭제) 시각.
        _events (tuple[DomainEvent, ...]): 누적된 도메인 이벤트 큐.
    """

    id: UUID = field(default_factory=uuid4)
    version: int = 0
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    _events: tuple[DomainEvent, ...] = field(default=(), repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """시간 필드 유효성 검사를 수행합니다.

        Raises:
            ValueError: `created_at` 또는 `updated_at`가 naive 이거나,
                `archived_at`가 naive 이거나, `updated_at < created_at`인 경우.
        """
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="created_at, updated_at")
        if self.updated_at < self.created_at:
            object.__setattr__(self, "updated_at", self.created_at)
        if self.archived_at is not None and self.archived_at.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="archived_at")

    def __eq__(self, other: Any) -> bool:
        """엔티티 동등성 비교.

        같은 구체 타입이면서 같은 `id`를 가질 때만 동일하다고 판단합니다.

        Args:
            other: 비교 대상.

        Returns:
            bool: 동등성 여부.
        """
        return type(other) is type(self) and self.id == other.id

    def __hash__(self) -> int:
        """엔티티 해시값을 반환합니다.

        타입과 `id`를 모두 포함해 해시 충돌 가능성을 낮춥니다.

        Returns:
            int: 해시값.
        """
        return hash((type(self), self.id))

    @classmethod
    def create(cls, now: datetime, **kwargs: Any) -> Self:
        """엔티티를 생성합니다.

        불변성을 위해 직접 초기화 대신 팩토리 메서드 사용을 권장합니다.

        Args:
            now: 생성/수정 시각(aware datetime, 보통 UTC).
            **kwargs: 엔티티 서브클래스의 추가 필드.

        Returns:
            Self: 생성된 엔티티 인스턴스.

        Raises:
            ValueError: `now`가 naive 인 경우.
        """
        if now.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="now")
        return cls(created_at=now, updated_at=now, **kwargs)

    def update(self, now: datetime, **kwargs: Any) -> Self:
        """엔티티를 갱신한 새 인스턴스를 반환합니다.

        `updated_at`과 `version`이 자동으로 갱신됩니다.

        Args:
            now: 갱신 기준 시각(aware datetime, 보통 UTC).
            **kwargs: 변경할 필드 값.

        Returns:
            Self: 변경이 반영된 새 엔티티.

        Raises:
            ValueError: `now`가 naive 이거나, `now < updated_at`인 경우.
        """
        if now.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="now")
        if now < self.updated_at:
            raise TimestampOrderError("updated_at", "now")
        return replace(self, updated_at=now, version=self.version + 1, **kwargs)

    def archive(self, now: datetime) -> Self:
        """엔티티를 보관(소프트 삭제) 처리한 새 인스턴스를 반환합니다.

        Args:
            now: 보관 시각(aware datetime, 보통 UTC).

        Returns:
            Self: 보관된 새 엔티티.

        Raises:
            ValueError: `now`가 naive 이거나, `now < updated_at`인 경우.
        """
        if now.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="now")
        if now < self.updated_at:
            raise TimestampOrderError("updated_at", "now")
        return replace(self, updated_at=now, version=self.version + 1, archived_at=now)

    def unarchive(self, now: datetime) -> Self:
        """엔티티를 보관 해제한 새 인스턴스를 반환합니다.

        Args:
            now: 보관 해제 시각(aware datetime, 보통 UTC).

        Returns:
            Self: 보관 해제된 새 엔티티.

        Raises:
            ValueError: `now`가 naive 인 경우.
        """
        if now.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="now")
        return replace(self, updated_at=now, archived_at=None, version=self.version + 1)

    def add_event(self, event: DomainEvent) -> Self:
        """도메인 이벤트를 큐에 추가하고, 이벤트 시각으로 갱신합니다.

        `updated_at`은 이벤트의 `occurred_at`으로, `version`은 +1 증가합니다.

        Args:
            event: 추가할 도메인 이벤트.

        Returns:
            Self: 이벤트가 누적된 새 엔티티.

        Raises:
            ValueError: `event`가 `DomainEvent` 프로토콜을 만족하지 않거나
                `occurred_at`이 naive 인 경우.
        """
        if not isinstance(event, DomainEvent) or event.occurred_at.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="event.occurred_at")
        return replace(
            self,
            _events=self._events + (event,),
            updated_at=event.occurred_at,
            version=self.version + 1,
        )

    def drain_events(self) -> tuple[tuple[DomainEvent, ...], Self]:
        """이벤트 큐를 배출하고, 큐가 비워진 새 엔티티를 반환합니다.

        Returns:
            tuple[tuple[DomainEvent, ...], Self]:
                첫 번째는 누적된 이벤트 튜플,
                두 번째는 이벤트 큐가 비워진 새 엔티티 인스턴스입니다.
        """
        events = self._events
        return events, replace(self, _events=())

    def peek_events(self) -> tuple[DomainEvent, ...]:
        """이벤트 큐를 비우지 않고 조회합니다.

        Returns:
            tuple[DomainEvent, ...]: 현재 누적된 이벤트 목록(불변 튜플).
        """
        return self._events


__all__ = ["DomainEvent", "Entity"]

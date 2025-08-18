"""도메인 이벤트 베이스 모듈.

- 본 모듈은 구현 편의를 위한 `BaseDomainEvent`를 제공합니다.
- 모든 이벤트는 `DomainEvent` 프로토콜(id: UUID, occurred_at: aware datetime)을 만족해야 합니다.
- **시간(occurred_at)은 외부에서 주입**해야 하며, naive datetime은 허용되지 않습니다.
- 아웃박스 패턴/로깅을 위한 직렬화 유틸(`payload()`, `to_outbox_record()`)을 포함합니다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from akbo.shared.domain.exceptions import TimestampMustBeTimezoneAwareError


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseDomainEvent:
    """구현 편의를 위한 도메인 이벤트 베이스 클래스.

    본 베이스는 이벤트가 갖추어야 할 **최소 공통 속성**과
    아웃박스/로깅을 위한 **직렬화 도우미**를 제공합니다.
    시간은 반드시 외부에서 주입되며, naive datetime은 거부됩니다.

    Attributes:
        id: 이벤트 식별자(기본값: `uuid4()`).
        occurred_at: 이벤트 발생 시각. **타임존 포함(aware) datetime**이어야 합니다.
        aggregate_id: (선택) 해당 이벤트가 소속된 애그리게이트 식별자.
        aggregate_type: (선택) 애그리게이트 타입명(예: `"Score"`).
        version: (선택) 애그리게이트 버전(낙관적 락/스냅샷 복구 등에서 유용).
        TYPE: (클래스 상수) 이벤트 타입 문자열. 지정하지 않으면 FQN
            (`{module}.{ClassName}`)이 사용됩니다.

    Note:
        - 본 클래스는 **Protocol 구현을 돕는 편의 계층**입니다.
          엄밀히는 `DomainEvent` 프로토콜만 충족하면 되므로,
          도메인별로 별도 이벤트 클래스를 직접 정의해도 무방합니다.
    """

    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime

    aggregate_id: UUID | None = None
    aggregate_type: str | None = None
    version: int | None = None

    TYPE: ClassVar[str | None] = None

    def __post_init__(self) -> None:
        """유효성 검증을 수행합니다.

        Raises:
            TimestampMustBeTimezoneAwareError: `occurred_at`이 naive datetime인 경우.
        """
        if self.occurred_at.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="occurred_at")

    @property
    def event_type(self) -> str:
        """이벤트 타입 문자열을 반환합니다.

        지정된 `TYPE`이 있으면 그 값을, 없으면 모듈 경로를 포함한
        정규화된 클래스 이름(FQN)을 반환합니다.

        Returns:
            str: 이벤트 타입 문자열.
        """
        return self.TYPE or f"{type(self).__module__}.{type(self).__name__}"

    def payload(self) -> Mapping[str, Any]:
        """아웃박스/로깅용 페이로드를 반환합니다.

        이벤트 본문에서 식별자(`id`)와 시간(`occurred_at`)을 제외한
        나머지 필드들만을 딕셔너리 형태로 제공합니다.

        Returns:
            Mapping[str, Any]: 직렬화 가능한 페이로드 맵.
        """
        d = asdict(self)
        d.pop("id", None)
        d.pop("occurred_at", None)
        return d

    def to_outbox_record(self) -> Mapping[str, Any]:
        """아웃박스/이벤트 로그에 저장하기 위한 표준 레코드를 생성합니다.

        Returns:
            Mapping[str, Any]: 다음 키를 포함한 표준 레코드
                - `"id"`: 이벤트 ID 문자열
                - `"type"`: 이벤트 타입 문자열
                - `"occurred_at"`: ISO-8601 문자열
                - `"payload"`: `payload()` 결과 맵
        """
        return {
            "id": str(self.id),
            "type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "payload": self.payload(),
        }


__all__ = ["BaseDomainEvent"]

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from datetime import datetime
from uuid import UUID, uuid4

import pytest

# 프로젝트 경로에 맞춰 import (예: shared/domain/domain_event.py)
from akbo.shared.domain.domain_event import BaseDomainEvent
from akbo.shared.domain.entity import DomainEvent, Entity
from akbo.shared.domain.exceptions import TimestampMustBeTimezoneAwareError

# ----- Stubs (상속형식) -----


@dataclass(frozen=True, slots=True, kw_only=True)
class EventStub(BaseDomainEvent):
    """테스트용 이벤트. BaseDomainEvent 상속."""

    TYPE: str = "test.event"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class Foo(Entity):
    name: str


# ======================== BaseDomainEvent: Construction ========================


class TestConstruction:
    def test_requires_aware_occurred_at(self):
        """naive 시각 거부를 검증합니다.

        Given:
            - 타임존 정보가 없는 naive `occurred_at`
        When:
            - `BaseDomainEvent`를 생성
        Then:
            - `TimestampMustBeTimezoneAwareError`가 발생해야 한다
        """
        with pytest.raises(TimestampMustBeTimezoneAwareError):
            BaseDomainEvent(occurred_at=datetime(2025, 1, 1, 0, 0, 0))  # noqa: DTZ001

    def test_accepts_aware_occurred_at(self, ko_tz):
        """aware 시각 수용을 검증합니다.

        Given:
            - 타임존 정보가 포함된 `occurred_at`(aware)
        When:
            - `BaseDomainEvent`를 생성
        Then:
            - `tzinfo`가 `None`이 아니다
        """
        e = BaseDomainEvent(occurred_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=ko_tz))
        assert e.occurred_at.tzinfo is not None

    def test_is_frozen_immutable(self, ko_tz):
        """동결(frozen) 불변성을 검증합니다.

        Given:
            - 정상적으로 생성된 이벤트 인스턴스
        When:
            - 필드 값을 변경 시도
        Then:
            - `FrozenInstanceError`가 발생해야 한다
        """
        e = BaseDomainEvent(occurred_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=ko_tz))
        with pytest.raises(FrozenInstanceError):
            e.occurred_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=ko_tz)


# ======================== BaseDomainEvent: Type & Payload ========================


class TestTypeAndPayload:
    def test_event_type_uses_type_if_defined(self, ko_tz):
        """TYPE 우선 적용을 검증합니다.

        Given:
            - `TYPE` 상수를 가진 서브클래스 이벤트
        When:
            - `event_type`을 조회
        Then:
            - `TYPE` 값이 반환된다
        """

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyEvt(BaseDomainEvent):
            TYPE: str = "score.created"
            score_id: UUID

        e = MyEvt(occurred_at=datetime(2025, 1, 1, tzinfo=ko_tz), score_id=uuid4())
        assert e.event_type == "score.created"

    def test_event_type_falls_back_to_fqn(self, ko_tz):
        """FQN 폴백을 검증합니다.

        Given:
            - `TYPE` 상수가 없는 서브클래스 이벤트
        When:
            - `event_type`을 조회
        Then:
            - 모듈 경로를 포함한 FQN 문자열이 반환된다
        """

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyEvtNoType(BaseDomainEvent):
            thing: str

        e = MyEvtNoType(occurred_at=datetime(2025, 1, 1, tzinfo=ko_tz), thing="x")
        assert "." in e.event_type  # FQN 형식 여부만 단정

    def test_payload_excludes_id_and_occurred_at(self, ko_tz):
        """payload 필드 제약을 검증합니다.

        Given:
            - 임의의 `BaseDomainEvent` 인스턴스
        When:
            - `payload()` 호출
        Then:
            - `id`와 `occurred_at` 키가 존재하지 않는다
        """
        e = BaseDomainEvent(
            occurred_at=datetime(2025, 1, 1, tzinfo=ko_tz),
            aggregate_type="Score",
            version=1,
        )
        p = e.payload()
        assert "id" not in p
        assert "occurred_at" not in p

    def test_to_outbox_record_shape(self, ko_tz):
        """아웃박스 레코드 스키마를 검증합니다.

        Given:
            - 임의의 `BaseDomainEvent` 인스턴스
        When:
            - `to_outbox_record()` 호출
        Then:
            - `id`, `type`, `occurred_at`, `payload` 키가 모두 존재한다
        """
        e = BaseDomainEvent(occurred_at=datetime(2025, 1, 1, tzinfo=ko_tz))
        rec = e.to_outbox_record()
        assert all(k in rec for k in ("id", "type", "occurred_at", "payload"))


# ======================== Protocol Compliance ========================


class TestProtocol:
    def test_runtime_checkable_protocol(self, ko_tz):
        """Protocol 준수를 검증합니다.

        Given:
            - `BaseDomainEvent`를 상속한 `EventStub`
        When:
            - `isinstance(stub, DomainEvent)` 검사
        Then:
            - `True`가 반환된다 (구조적 합치)
        """
        stub = EventStub(occurred_at=datetime(2025, 1, 1, tzinfo=ko_tz))
        assert isinstance(stub, DomainEvent)


# ======================== Entity Interaction (Acceptance) ========================


class TestEntityIntegration:
    def test_add_event_updates_time(self, ko_tz):
        """엔티티-이벤트 상호작용(시간 갱신)을 검증합니다.

        Given:
            - t0에 생성된 `Foo`
            - t1에 발생한 `EventStub`
        When:
            - `add_event(evt)` 호출
        Then:
            - `updated_at == t1`
        """
        t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=ko_tz)
        t1 = datetime(2025, 1, 1, 0, 0, 1, tzinfo=ko_tz)
        foo = Foo.create(now=t0, name="bar")
        evt = EventStub(occurred_at=t1)
        foo2 = foo.add_event(evt)
        assert foo2.updated_at == t1

    def test_add_event_appends_queue_len_1(self, ko_tz):
        """이벤트 큐 적재를 검증합니다.

        Given:
            - t0에 생성된 `Foo`
        When:
            - t1 이벤트로 `add_event` 호출
        Then:
            - 이벤트 큐 길이는 1
        """
        t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=ko_tz)
        t1 = datetime(2025, 1, 1, 0, 0, 1, tzinfo=ko_tz)
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(EventStub(occurred_at=t1))
        assert len(foo2.peek_events()) == 1

    def test_add_event_increments_version(self, ko_tz):
        """버전 증가를 검증합니다.

        Given:
            - t0에 생성된 `Foo`
        When:
            - t0 시각 이벤트로 `add_event` 호출
        Then:
            - `version`이 1 증가한다
        """
        t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=ko_tz)
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(EventStub(occurred_at=t0))
        assert foo2.version == foo.version + 1

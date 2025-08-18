"""`akbo.shared.domain.entity.Entity` 테스트."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from akbo.shared.domain.entity import Entity
from akbo.shared.domain.exceptions import (
    TimestampMustBeTimezoneAwareError,
    TimestampOrderError,
)


@pytest.fixture
def t0(ko_tz: datetime.tzinfo) -> datetime:
    """테스트 기준 시각(t0)을 반환합니다."""
    return datetime(2025, 1, 1, 0, 0, 0, tzinfo=ko_tz)


@pytest.fixture
def t1(ko_tz: datetime.tzinfo) -> datetime:
    """테스트 기준 시각(t1)을 반환합니다."""
    return datetime(2025, 1, 1, 1, 0, 1, tzinfo=ko_tz)


@dataclass(frozen=True, slots=True, kw_only=True)
class EventStub:
    """테스트용 도메인 이벤트 스텁."""

    id: UUID
    occurred_at: datetime


@pytest.fixture
def make_event(ko_tz):
    """`EventStub` 인스턴스를 생성하는 팩토리 함수를 반환합니다."""

    def _make(ts: datetime | None = None) -> EventStub:
        return EventStub(id=uuid4(), occurred_at=ts or datetime.now(ko_tz))

    return _make


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class Foo(Entity):
    """테스트용 엔티티 구현체."""

    name: str


class TestCreate:
    """`Entity.create` 메서드 테스트."""

    def test_rejects_naive_now(self):
        """타임존 없는 시각으로 생성 시 예외를 발생시키는지 테스트합니다.

        Given:
            - 타임존 정보가 없는(naive) `datetime` 객체를 준비합니다.
        When:
            - `Foo.create`를 해당 시각으로 호출합니다.
        Then:
            - `TimestampMustBeTimezoneAwareError` 예외가 발생해야 합니다.
        """
        naive = datetime(2025, 1, 1, 0, 0, 0)
        with pytest.raises(TimestampMustBeTimezoneAwareError):
            Foo.create(now=naive, name="x")

    def test_sets_created_at_equals_now(self, t0):
        """`created_at`이 `now`와 동일하게 설정되는지 테스트합니다.

        Given:
            - 기준 시각 `t0`을 준비합니다.
        When:
            - `Foo.create`를 `t0` 시각으로 호출합니다.
        Then:
            - 생성된 엔티티의 `created_at`은 `t0`과 같아야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        assert foo.created_at == t0

    def test_sets_updated_at_equals_now(self, t0):
        """`updated_at`이 `now`와 동일하게 설정되는지 테스트합니다.

        Given:
            - 기준 시각 `t0`을 준비합니다.
        When:
            - `Foo.create`를 `t0` 시각으로 호출합니다.
        Then:
            - 생성된 엔티티의 `updated_at`은 `t0`과 같아야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        assert foo.updated_at == t0

    def test_initial_version_zero(self, t0):
        """초기 버전이 0으로 설정되는지 테스트합니다.

        Given:
            - 기준 시각 `t0`을 준비합니다.
        When:
            - `Foo.create`를 호출합니다.
        Then:
            - 생성된 엔티티의 `version`은 0이어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        assert foo.version == 0

    def test_initial_archived_none(self, t0):
        """초기 `archived_at`이 `None`으로 설정되는지 테스트합니다.

        Given:
            - 기준 시각 `t0`을 준비합니다.
        When:
            - `Foo.create`를 호출합니다.
        Then:
            - 생성된 엔티티의 `archived_at`은 `None`이어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        assert foo.archived_at is None

    def test_initial_events_empty(self, t0):
        """초기 이벤트 큐가 비어있는지 테스트합니다.

        Given:
            - 기준 시각 `t0`을 준비합니다.
        When:
            - `Foo.create`를 호출합니다.
        Then:
            - 생성된 엔티티의 이벤트 큐는 비어 있어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        assert tuple(foo.peek_events()) == ()


class TestUpdate:
    """`Entity.update` 메서드 테스트."""

    def test_changes_field_value(self, t0, t1):
        """필드 값이 올바르게 변경되는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `t1` 시각에 `update`를 호출하여 `name` 필드를 변경합니다.
        Then:
            - 반환된 새 엔티티의 `name` 필드 값이 변경되어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.update(now=t1, name="baz")
        assert foo2.name == "baz"

    def test_increments_version(self, t0, t1):
        """`version`이 1 증가하는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `t1` 시각에 `update`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 `version`이 기존보다 1 커야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.update(now=t1, name="baz")
        assert foo2.version == foo.version + 1

    def test_sets_updated_at_to_now(self, t0, t1):
        """`updated_at`이 `now`로 갱신되는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `t1` 시각에 `update`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 `updated_at`이 `t1`과 같아야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.update(now=t1, name="baz")
        assert foo2.updated_at == t1

    def test_rejects_time_travel(self, t0):
        """과거 시각으로 업데이트 시 예외를 발생시키는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `t0`보다 이전 시각으로 `update`를 호출합니다.
        Then:
            - `TimestampOrderError` 예외가 발생해야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        earlier = t0 - timedelta(seconds=1)
        with pytest.raises(TimestampOrderError):
            foo.update(now=earlier, name="baz")

    def test_returns_new_instance(self, t0):
        """새로운 인스턴스를 반환하는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `update`를 호출합니다.
        Then:
            - 반환된 객체는 원본 객체와 다른 인스턴스여야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.update(now=t0, name="baz")
        assert foo2 is not foo


class TestArchiveUnarchive:
    """`Entity.archive` 및 `unarchive` 메서드 테스트."""

    def test_archive_sets_archived_at_to_now(self, t0, t1):
        """`archive` 시 `archived_at`이 `now`로 설정되는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `t1` 시각에 `archive`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 `archived_at`이 `t1`과 같아야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo_arch = foo.archive(now=t1)
        assert foo_arch.archived_at == t1

    def test_archive_increments_version(self, t0, t1):
        """`archive` 시 `version`이 1 증가하는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `t1` 시각에 `archive`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 `version`이 기존보다 1 커야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo_arch = foo.archive(now=t1)
        assert foo_arch.version == foo.version + 1

    def test_archive_rejects_time_travel(self, t0):
        """과거 시각으로 `archive` 시 예외를 발생시키는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `t0`보다 이전 시각으로 `archive`를 호출합니다.
        Then:
            - `TimestampOrderError` 예외가 발생해야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        earlier = t0 - timedelta(seconds=1)
        with pytest.raises(TimestampOrderError):
            foo.archive(now=earlier)

    def test_unarchive_clears_archived_at(self, t0, t1):
        """`unarchive` 시 `archived_at`이 `None`으로 설정되는지 테스트합니다.

        Given:
            - `t0`에 생성하고 `t1`에 보관된 엔티티를 준비합니다.
        When:
            - `t1` 시각에 `unarchive`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 `archived_at`이 `None`이어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo_arch = foo.archive(now=t1)
        foo_unarch = foo_arch.unarchive(now=t1)
        assert foo_unarch.archived_at is None

    def test_unarchive_increments_version(self, t0, t1):
        """`unarchive` 시 `version`이 1 증가하는지 테스트합니다.

        Given:
            - `t0`에 생성하고 `t1`에 보관된 엔티티를 준비합니다.
        When:
            - `t1` 시각에 `unarchive`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 `version`이 보관된 엔티티보다 1 커야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo_arch = foo.archive(now=t1)
        foo_unarch = foo_arch.unarchive(now=t1)
        assert foo_unarch.version == foo_arch.version + 1

    def test_unarchive_rejects_naive_now(self, t0):
        """타임존 없는 `now`로 `unarchive` 시 예외를 발생시키는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성하고, 보관된 엔티티를 준비합니다.
        When:
            - `unarchive`를 호출합니다.
        Then:
            - `TimestampMustBeTimezoneAwareError` 예외가 발생해야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo_arch = foo.archive(now=t0)
        with pytest.raises(TimestampMustBeTimezoneAwareError):
            foo_arch.unarchive(now=datetime(2025, 1, 1, 0, 0, 0))


class TestEvents:
    """도메인 이벤트 관련 메서드 테스트."""

    def test_add_event_sets_updated_at(self, t0, make_event):
        """`add_event` 시 `updated_at`이 이벤트 발생 시각으로 설정되는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성하고, 별도의 도메인 이벤트를 준비합니다.
        When:
            - `add_event`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 `updated_at`이 이벤트의 `occurred_at`과 같아야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        ev = make_event()
        foo2 = foo.add_event(ev)
        assert foo2.updated_at == ev.occurred_at

    def test_add_event_increments_version(self, t0, make_event):
        """`add_event` 시 `version`이 1 증가하는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `add_event`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 `version`이 기존보다 1 커야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(make_event())
        assert foo2.version == foo.version + 1

    def test_add_event_appends_queue_length_1(self, t0, make_event):
        """`add_event` 시 이벤트 큐에 이벤트가 추가되는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성합니다.
        When:
            - `add_event`를 호출합니다.
        Then:
            - 반환된 새 엔티티의 이벤트 큐 길이가 1이어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(make_event())
        assert len(foo2.peek_events()) == 1

    def test_add_event_rejects_naive_event(self, t0):
        """타임존 없는 이벤트를 추가 시 예외를 발생시키는지 테스트합니다.

        Given:
            - `t0` 시각에 엔티티를 생성하고, `occurred_at`이 naive인 이벤트를 준비합니다.
        When:
            - `add_event`를 해당 이벤트로 호출합니다.
        Then:
            - `TimestampMustBeTimezoneAwareError` 예외가 발생해야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")

        @dataclass(frozen=True, slots=True, kw_only=True)
        class NaiveEvent:
            id: UUID
            occurred_at: datetime

        ev = NaiveEvent(id=uuid4(), occurred_at=datetime(2025, 1, 1, 0, 0, 0))
        with pytest.raises(TimestampMustBeTimezoneAwareError):
            foo.add_event(ev)

    def test_drain_returns_events_length_1(self, t0, make_event):
        """`drain_events`가 올바른 수의 이벤트를 반환하는지 테스트합니다.

        Given:
            - 이벤트가 하나 추가된 엔티티를 준비합니다.
        When:
            - `drain_events`를 호출합니다.
        Then:
            - 반환된 이벤트 목록의 길이가 1이어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(make_event())
        events, _ = foo2.drain_events()
        assert len(events) == 1

    def test_drain_returns_instance_with_empty_queue(self, t0, make_event):
        """`drain_events`가 비워진 큐를 가진 새 인스턴스를 반환하는지 테스트합니다.

        Given:
            - 이벤트가 하나 추가된 엔티티를 준비합니다.
        When:
            - `drain_events`를 호출합니다.
        Then:
            - 함께 반환된 새 엔티티의 이벤트 큐는 비어 있어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(make_event())
        _, foo3 = foo2.drain_events()
        assert len(foo3.peek_events()) == 0

    def test_drain_does_not_mutate_original_queue(self, t0, make_event):
        """`drain_events`가 원본 엔티티를 변경하지 않는지 테스트합니다.

        Given:
            - 이벤트가 하나 추가된 엔티티를 준비합니다.
        When:
            - `drain_events`를 호출합니다.
        Then:
            - 원본 엔티티의 이벤트 큐는 그대로 유지되어야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(make_event())
        _, _ = foo2.drain_events()
        assert len(foo2.peek_events()) == 1


class TestEqualityHash:
    """엔티티 동등성 및 해시 테스트."""

    def test_equality_same_type_same_id_true(self, t0):
        """타입과 ID가 같으면 동등하다고 판단하는지 테스트합니다.

        Given:
            - 동일한 ID를 가진 두 개의 `Foo` 엔티티를 생성합니다.
        When:
            - 두 엔티티를 `==` 연산자로 비교합니다.
        Then:
            - 결과는 `True`여야 합니다.
        """
        same_id = uuid4()
        a = Foo.create(now=t0, id=same_id, name="A")
        b = Foo.create(now=t0, id=same_id, name="B")
        assert a == b

    def test_hash_same_type_same_id_equal_hash(self, t0):
        """타입과 ID가 같으면 해시값도 같은지 테스트합니다.

        Given:
            - 동일한 ID를 가진 두 개의 `Foo` 엔티티를 생성합니다.
        When:
            - 두 엔티티의 해시값을 비교합니다.
        Then:
            - 두 해시값은 같아야 합니다.
        """
        same_id = uuid4()
        a = Foo.create(now=t0, id=same_id, name="A")
        b = Foo.create(now=t0, id=same_id, name="B")
        assert hash(a) == hash(b)

    def test_equality_different_type_same_id_false(self, t0):
        """ID가 같아도 타입이 다르면 동등하지 않다고 판단하는지 테스트합니다.

        Given:
            - 동일한 ID를 가졌지만 타입이 다른 두 엔티티(`Foo`, `Bar`)를 생성합니다.
        When:
            - 두 엔티티를 `!=` 연산자로 비교합니다.
        Then:
            - 결과는 `True`여야 합니다.
        """
        same_id = uuid4()

        @dataclass(frozen=True, slots=True, kw_only=True, eq=False)
        class Bar(Entity):
            name: str

        a = Foo.create(now=t0, id=same_id, name="A")
        c = Bar.create(now=t0, id=same_id, name="C")
        assert a != c

    def test_equality_ignores_non_identity_fields(self, t0):
        """ID 외 다른 필드는 동등성 비교에 영향을 주지 않는지 테스트합니다.

        Given:
            - 동일한 ID를 가진 엔티티 `a`를 생성합니다.
            - `a`를 업데이트하여 `name`이 다른 `a2`를 생성합니다.
        When:
            - `a`와 `a2`를 `==` 연산자로 비교합니다.
        Then:
            - 결과는 `True`여야 합니다. `a`와 `a2`는 같은 ID를 가집니다.
        """
        same_id = uuid4()
        a = Foo.create(now=t0, id=same_id, name="A")
        a2 = a.update(now=t0, name="AA")
        assert a == a2


class TestPostInitEdge:
    """`Entity.__post_init__` 엣지 케이스 테스트."""

    def test_aligns_updated_at_when_less(self, t0):
        """`updated_at`이 `created_at`보다 빠를 때 자동 보정되는지 테스트합니다.

        Given:
            - `updated_at`이 `created_at`보다 이전인 엔티티를 직접 초기화합니다.
        When:
            - 엔티티 인스턴스가 생성됩니다 (`__post_init__` 호출).
        Then:
            - `updated_at`은 `created_at`과 동일한 값으로 보정되어야 합니다.
        """
        later = t0 + timedelta(seconds=10)
        x = Foo(id=uuid4(), name="x", created_at=later, updated_at=t0, archived_at=None)
        assert x.updated_at == x.created_at


class TestImmutability:
    """엔티티 불변성 테스트."""

    def test_create_returns_new_instance(self, t0):
        """`create`가 새 인스턴스를 반환하는지 확인합니다.

        Given:
            - 기준 시각 `t0`
        When:
            - `Foo.create`를 호출합니다.
        Then:
            - 반환된 값은 `Foo`의 인스턴스여야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        assert isinstance(foo, Foo)

    def test_update_returns_new_instance(self, t0, t1):
        """`update`가 새 인스턴스를 반환하는지 확인합니다.

        Given:
            - `t0`에 생성된 엔티티 `foo`.
        When:
            - `foo.update`를 호출합니다.
        Then:
            - 반환된 `foo2`는 `foo`와 다른 객체여야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.update(now=t1, name="baz")
        assert foo2 is not foo

    def test_archive_returns_new_instance(self, t0, t1):
        """`archive`가 새 인스턴스를 반환하는지 확인합니다.

        Given:
            - `t0`에 생성된 엔티티 `foo`.
        When:
            - `foo.archive`를 호출합니다.
        Then:
            - 반환된 `foo2`는 `foo`와 다른 객체여야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.archive(now=t1)
        assert foo2 is not foo

    def test_unarchive_returns_new_instance(self, t0, t1):
        """`unarchive`가 새 인스턴스를 반환하는지 확인합니다.

        Given:
            - `t0`에 생성되고 `t1`에 보관된 엔티티 `foo_arch`.
        When:
            - `foo_arch.unarchive`를 호출합니다.
        Then:
            - 반환된 `foo_unarch`는 `foo_arch`와 다른 객체여야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo_arch = foo.archive(now=t1)
        foo_unarch = foo_arch.unarchive(now=t1)
        assert foo_unarch is not foo_arch

    def test_add_event_returns_new_instance(self, t0, make_event):
        """`add_event`가 새 인스턴스를 반환하는지 확인합니다.

        Given:
            - `t0`에 생성된 엔티티 `foo`.
        When:
            - `foo.add_event`를 호출합니다.
        Then:
            - 반환된 `foo2`는 `foo`와 다른 객체여야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(make_event())
        assert foo2 is not foo

    def test_drain_events_returns_new_instance(self, t0, make_event):
        """`drain_events`가 새 인스턴스를 반환하는지 확인합니다.

        Given:
            - 이벤트가 추가된 엔티티 `foo2`.
        When:
            - `foo2.drain_events`를 호출합니다.
        Then:
            - 반환된 `foo3`는 `foo2`와 다른 객체여야 합니다.
        """
        foo = Foo.create(now=t0, name="bar")
        foo2 = foo.add_event(make_event())
        _, foo3 = foo2.drain_events()
        assert foo3 is not foo2

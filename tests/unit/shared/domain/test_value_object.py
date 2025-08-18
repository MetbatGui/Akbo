"""`akbo.shared.domain.value_object` 테스트."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from datetime import datetime, timedelta
from typing import Any

import pytest

from akbo.shared.domain.exceptions import TimestampMustBeTimezoneAwareError
from akbo.shared.domain.value_object import SingleValueObject, ValueObject

# ========================== 테스트용 실제 구현체들 ==========================


MAX_NAME_LENGTH = 100


@dataclass(frozen=True, slots=True, kw_only=True)
class Name(SingleValueObject[str]):
    """사용자/도메인 명칭 값 객체.

    - normalize: 앞뒤 공백 제거
    - validate: 비어 있지 않음, 최대 길이 100
    """

    def _normalize_value(self, v: str) -> str:
        return v.strip()

    def _validate_value(self, v: str) -> None:
        if not v:
            raise ValueError("Name empty.")
        if len(v) > MAX_NAME_LENGTH:
            raise ValueError("Name too long.")


@dataclass(frozen=True, slots=True, kw_only=True)
class AwareDateTime(SingleValueObject[datetime]):
    """타임존 정보가 있는(aware) datetime만 허용하는 값 객체."""

    def _validate_value(self, v: datetime) -> None:
        if v.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="value")


@dataclass(frozen=True, slots=True, kw_only=True)
class Period(ValueObject):
    """기간 값 객체: [start, end].

    - validate: 두 값 모두 aware 이어야 하며, end >= start
    """

    start: datetime
    end: datetime

    def _validate(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise TimestampMustBeTimezoneAwareError(field="start/end")
        if self.end < self.start:
            raise ValueError("End before start.")


@dataclass(frozen=True, slots=True, kw_only=True)
class Slug(ValueObject):
    """슬러그 값 객체.

    - normalize: 트리밍 + 소문자화
    """

    text: str

    def _normalize(self) -> dict[str, Any] | None:
        x = self.text.strip().lower()
        return {"text": x} if x != self.text else None


# ========================== SingleValueObject: Normalize ==========================


class TestSingleValueNormalize:
    """단일값 VO의 정규화 동작 테스트."""

    def test_trims_whitespace(self):
        """공백 제거 정규화를 검증합니다.

        Given:
            - 앞뒤 공백이 포함된 문자열 "  Alice  "
        When:
            - Name(value="  Alice  ")로 인스턴스 생성
        Then:
            - 내부 저장 값은 "Alice" 여야 합니다.
        """
        n = Name(value="  Alice  ")
        assert n.value == "Alice"


# ========================== SingleValueObject: Validate ==========================


class TestSingleValueValidate:
    """단일값 VO의 검증 동작 테스트."""

    def test_rejects_empty(self):
        """빈 문자열 거부를 검증합니다.

        Given:
            - 빈 문자열 ""
        When:
            - Name(value="") 생성 시도
        Then:
            - ValueError 예외가 발생해야 합니다.
        """
        with pytest.raises(ValueError, match="Name empty."):
            Name(value="")

    def test_rejects_naive_datetime(self):
        """naive datetime 거부를 검증합니다.

        Given:
            - tzinfo가 없는 naive datetime
        When:
            - AwareDateTime(value=naive) 생성 시도
        Then:
            - TimestampMustBeTimezoneAwareError 예외가 발생해야 합니다.
        """
        with pytest.raises(TimestampMustBeTimezoneAwareError):
            AwareDateTime(value=datetime(2025, 1, 1, 0, 0, 0))  # noqa: DTZ001

    def test_accepts_aware_datetime(self, ko_tz):
        """aware datetime 수용을 검증합니다.

        Given:
            - tzinfo가 있는 aware datetime
        When:
            - AwareDateTime(value=aware) 생성
        Then:
            - 내부 값의 tzinfo는 None이 아니어야 합니다.
        """
        v = AwareDateTime(value=datetime(2025, 1, 1, 0, 0, 0, tzinfo=ko_tz))
        assert v.value.tzinfo is not None


# ========================== SingleValueObject: Immutability & Convenience ====================


class TestSingleValueImmutabilityConvenience:
    """단일값 VO의 불변성과 편의 메서드 테스트."""

    def test_is_frozen_immutable(self):
        """불변성(frozen dataclass)을 검증합니다.

        Given:
            - Name("Alice") 인스턴스
        When:
            - value 필드 변경 시도
        Then:
            - FrozenInstanceError 예외가 발생해야 합니다.
        """
        n = Name(value="Alice")
        with pytest.raises(FrozenInstanceError):
            n.value = "Bob"

    def test_as_primitive_returns_underlying(self):
        """원시 표현 반환을 검증합니다.

        Given:
            - Name("Alice") 인스턴스
        When:
            - as_primitive() 호출
        Then:
            - "Alice"가 반환되어야 합니다.
        """
        n = Name(value="Alice")
        assert n.as_primitive() == "Alice"

    def test_str_returns_value_string(self):
        """문자열 표현을 검증합니다.

        Given:
            - Name("Alice") 인스턴스
        When:
            - str(n) 호출
        Then:
            - "Alice"가 반환되어야 합니다.
        """
        n = Name(value="Alice")
        assert str(n) == "Alice"


# ========================== ValueObject (multi-field) ==========================


class TestMultiFieldValueObject:
    """다필드 VO의 정규화/검증 파이프라인 테스트."""

    def test_period_rejects_backward_range(self, ko_tz):
        """역순 기간(end < start) 거부를 검증합니다.

        Given:
            - start=01:00:00, end=00:59:59 (end < start)
        When:
            - Period(start, end) 생성 시도
        Then:
            - ValueError 예외가 발생해야 합니다.
        """
        start = datetime(2025, 1, 1, 1, 0, 0, tzinfo=ko_tz)
        end = start - timedelta(seconds=1)
        with pytest.raises(ValueError, match="End before start."):
            Period(start=start, end=end)

    def test_period_requires_aware(self):
        """start/end 필드의 aware 강제를 검증합니다.

        Given:
            - naive start/end
        When:
            - Period(start, end) 생성 시도
        Then:
            - TimestampMustBeTimezoneAwareError 예외가 발생해야 합니다.
        """
        with pytest.raises(TimestampMustBeTimezoneAwareError):
            Period(
                start=datetime(2025, 1, 1, 0, 0, 0),  # noqa: DTZ001
                end=datetime(2025, 1, 1, 0, 0, 1),  # noqa: DTZ001
            )

    def test_slug_normalize_lower_and_trim(self):
        """_normalize 파이프라인에 의한 필드 치환을 검증합니다.

        Given:
            - "  HeLLo  " 입력
        When:
            - Slug(text="  HeLLo  ") 생성
        Then:
            - 내부 `text`는 "hello" 여야 합니다.
        """
        s = Slug(text="  HeLLo  ")
        assert s.text == "hello"

"""값 객체(Value Object) 베이스 모듈.

본 모듈은 DDD 스타일의 값 객체를 위한 두 가지 베이스 클래스를 제공합니다.

- `ValueObject`: 여러 필드를 갖는 값 객체까지 포괄하는 일반 베이스.
  - 생성 직후 `__post_init__`에서 `_normalize()` → `_validate()` 순으로 후처리합니다.
  - 불변(`frozen=True`), `slots=True`, `kw_only=True` 정책을 따릅니다.
- `SingleValueObject[T]`: 단일 필드 `value: T`를 갖는 값 객체 전용 베이스.
  - `_normalize()`가 내부에서 `_normalize_value(value)`를 호출해 입력값 정규화를 수행하고,
    `_validate()`가 `_validate_value(value)`를 호출해 도메인 검증을 수행합니다.

Note:
    - 정규화(normalize)는 **표현 통일**(트리밍, 대소문자 규칙, 중복 제거 등)만 담당해야 하며
      부작용이 없어야 합니다.
    - 검증(validate)은 **도메인 불변식 위반 시 예외**를 발생시켜야 합니다.
    - 경계(직렬화/DB/전송)로 값을 내보낼 때는 `as_primitive()` 사용을 권장합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class ValueObject:
    """DDD 값 객체 베이스.

    생성 직후 `__post_init__`에서 `_normalize()` → `_validate()` 순으로 호출되어
    입력값을 정규화한 뒤 도메인 규칙을 검증합니다. 이후에는 완전 불변입니다.
    """

    def _normalize(self) -> dict[str, Any] | None:
        """입력값 정규화를 수행합니다.

        서브클래스에서 필요할 때만 오버라이드하세요. 변경할 필드가 있을 경우
        `{필드명: 새값}` 딕셔너리를 반환하고, 없다면 `None`을 반환하세요.

        Returns:
            dict[str, Any] | None: 초기 정규화로 교체할 필드 맵 또는 `None`.
        """
        return None

    def _validate(self) -> None:
        """정규화 이후 도메인 규칙을 검증합니다.

        서브클래스에서 필요할 때만 오버라이드하세요. 불변식 위반 시 예외를 발생시키고,
        정상이라면 아무 것도 하지 않습니다.

        Raises:
            Exception: 임의의 도메인 규칙 위반 예외(예: `ValueError` 등).
        """
        return

    def __post_init__(self) -> None:
        """정규화 후 검증을 실행합니다.

        내부적으로만 사용되며, `frozen` 제약을 깨지 않기 위해 초기화 시에 한해
        `object.__setattr__`로 정규화 결과를 반영합니다.
        """
        updates = self._normalize()
        if updates:
            for k, v in updates.items():
                object.__setattr__(self, k, v)
        self._validate()


@dataclass(frozen=True, slots=True, kw_only=True)
class SingleValueObject[T](ValueObject):
    """단일 필드 `value: T`를 보유하는 값 객체 베이스.

    `_normalize()`는 내부에서 `_normalize_value(value)`를 호출해 입력값을 정규화하고,
    `_validate()`는 `_validate_value(value)`를 호출해 도메인 검증을 수행합니다.

    Attributes:
        value: 단일 원시/VO 값. 정규화 및 검증의 대상입니다.
    """

    value: T

    def _normalize_value(self, v: T) -> T:
        """단일 값에 대한 정규화를 수행합니다.

        기본 구현은 입력을 그대로 반환합니다. 필요한 경우 서브클래스에서
        트리밍, 대소문자 규칙, 정밀도 절단 등의 정규화를 구현하세요.

        Args:
            v (T): 입력 값.

        Returns:
            T: 정규화된 값.
        """
        return v

    def _validate_value(self, v: T) -> None:
        """단일 값에 대한 도메인 검증을 수행합니다.

        기본 구현은 아무 것도 하지 않습니다. 서브클래스에서 범위/패턴/비어있음
        등의 불변식을 검사하고, 위반 시 예외를 발생시키세요.

        Args:
            v (T): 검증 대상 값.

        Raises:
            Exception: 임의의 도메인 규칙 위반 예외(예: `ValueError` 등).
        """
        return

    def _normalize(self) -> dict[str, Any] | None:
        """단일 값 정규화를 실행하고 변경 시 교체 맵을 반환합니다.

        Returns:
            dict[str, Any] | None: `{"value": 정규화값}` 또는 변경이 없으면 `None`.
        """
        v2 = self._normalize_value(self.value)
        return {"value": v2} if v2 != self.value else None

    def _validate(self) -> None:
        """단일 값에 대한 도메인 검증을 실행합니다."""
        self._validate_value(self.value)

    def as_primitive(self) -> T:
        """경계 계층(직렬화/저장/전송)을 위한 원시 표현을 반환합니다.

        Returns:
            T: 외부 세계가 이해하는 원시 값 표현.
        """
        return self.value

    def __str__(self) -> str:
        """문자열 표현을 반환합니다.

        Returns:
            str: `value`의 문자열 변환 결과.
        """
        return str(self.value)


__all__ = ["ValueObject", "SingleValueObject"]

from __future__ import annotations


class DomainError(Exception):
    """도메인 계층에서 발생하는 예외의 기본 클래스."""


class TimestampMustBeTimezoneAwareError(DomainError, ValueError):
    """타임존 정보가 없는(datetime.tzinfo가 None) 시간 값일 때 발생하는 예외.

    Attributes:
        field: 검증 대상 필드명.
    """

    def __init__(self, field: str = "timestamp") -> None:
        super().__init__(f"{field} 값은 타임존 정보가 있는(aware) datetime이어야 합니다(UTC 권장).")
        self.field = field


class TimestampOrderError(DomainError, ValueError):
    """시간 값의 선후 관계가 잘못되었을 때 발생하는 예외.

    예: now가 updated_at보다 과거인 경우 등.

    Attributes:
        earlier: 기준이 되는 더 이른 시각의 필드명.
        later: 기준이 되는 더 늦은 시각의 필드명.
    """

    def __init__(self, earlier: str, later: str) -> None:
        super().__init__(f"{later} 값은 {earlier} 이상이어야 합니다.")
        self.earlier = earlier
        self.later = later


__all__ = [
    "DomainError",
    "TimestampMustBeTimezoneAwareError",
    "TimestampOrderError",
]

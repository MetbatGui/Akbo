from __future__ import annotations

import datetime

import pytest


@pytest.fixture
def ko_tz() -> datetime.tzinfo:
    return datetime.timezone(datetime.timedelta(hours=9))

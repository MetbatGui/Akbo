set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default: dev

# 개발 서버
dev:
    uv run uvicorn akbo.main:app --reload

unit-test:
    uv run pytest unit/

lint:
    uvx ruff check src/akbo

format:
    uvx ruff format src/akbo

type-check:
    uv run mypy src/akbo
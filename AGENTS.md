# Project Conventions

## Testing
- Run tests: `pytest`
- Lint: `ruff check .`
- Typecheck: `mypy src`

## Architecture
- Modular monolith with domain-driven boundaries
- Service layer pattern
- Async SQLAlchemy 2.0
- Pydantic v2 for validation

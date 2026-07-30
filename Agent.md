# Agent.md

Repository guidance for AI coding agents working on the *cahiers de doléances* project.

## Toolchain

- Python **>=3.12**. Dependencies managed with **uv**, not pip/poetry: `uv sync`.
- Run everything through uv: `uv run <cmd>` (or `source .venv/bin/activate`).

## Commands

- Install: `uv sync`
- Seed demo DB: `uv run python -m database.seed_mock`
- Run Gradio app: `uv run python gradio_app/app.py`
- Lint: `uv run ruff check .`
- Pre-commit: `uv run pre-commit run --all-files`
- All tests: `uv run pytest -vv`
- One file: `uv run pytest tests/integration/test_extraction.py -v`
- One test: `uv run pytest tests/integration/test_extraction.py::test_extracted_text_contains_phrase -v`

## Stale config — do not trust

- `tox.ini` references **poetry** and `py310`; the project actually uses **uv** and Python >=3.12. `tox` will fail — use `uv run pytest` instead. (README's "Tester avec Tox" section is outdated.)
- `[tool.setuptools.packages.find]` in `pyproject.toml` includes only `cahier_doleances*`. The `database` and `gradio_app` packages are **not installed**; importing them works only because the repo root is on `sys.path`. Always run commands from the repo root.

## Architecture

Three top-level packages, all imported as top-level modules (`from database.models import ...`, `from cahier_doleances.extraction import ...`):

- `cahier_doleances/` — extraction library. Pipeline: `extraction/extract_text.py::extract_pdf` (PyMuPDF) → `extraction/persist.py::save_extraction` → DB.
- `database/` — SQLAlchemy models (`models.py`: `Contribution`, `Extraction`, ...), engine (`db.py::get_engine`), Alembic migrations (`database/migrations/versions/`), `seed_mock.py`.
- `gradio_app/` — Gradio UI. Entry point `gradio_app/app.py`; views in `gradio_app/views/`.

End-to-end flow: PDF → text extraction → persisted to PostgreSQL → browse/annotate via Gradio.

## Database

- Connection from `.env`: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
- **Tests** use an in-memory SQLite engine (fixture `engine` in `tests/conftest.py` and `tests/integration/conftest.py`) — never real Postgres. Don't configure `.env` to run the test suite.
- Migrations via Alembic (`alembic.ini`, `script_location = database/migrations`).

## Pre-commit guards

- `check-added-large-files` rejects files > **500 KB**: never commit PDFs, DB dumps, or large data blobs.
- `gitleaks` blocks secrets; `ruff` autofixes; YAML/whitespace hooks enforce.

## Tests

Framework: **pytest**, **functions only** (no `unittest.TestCase`).

- `@pytest.mark.parametrize` for one behavior across multiple inputs — don't duplicate tests or put `if/else` branches in a test body.
- One test = one behavior; several small parametrized tests beat one big assertion cascade.
- Shared fixtures live in `conftest.py`, typed (`-> Path`, `-> Iterator[Engine]`).
- Integration tests use the real reference PDF `tests/data/Cahier_citoyen_test.pdf` (290 pages) + the `sqlite:///:memory:` `engine` fixture. Page categories used by tests: typed/valid (PyMuPDF extracts clean text), blank/empty (≈0 chars), handwritten/OCR-garbage (unusable output). See thresholds in `tests/integration/test_extraction.py`.
- Naming: `test_<subject>_<expected_condition>` in snake_case.

## Python conventions

- English docstrings, Google style; every module starts with a one-line docstring.
- Pydantic models for request/response validation (not raw dicts/dataclasses).
- Logs in English.

## Workflow

- Verify before finishing: `uv run ruff check .` then `uv run pytest -vv`.
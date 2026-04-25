test:
    uv run pytest

test-cov:
    uv run pytest --cov-report term --cov-report html:.coverage-html --cov src/atomforge

test-cov-sandbox:
    UV_CACHE_DIR=/tmp/uv-cache uv run pytest --cov-report term --cov-report html:.coverage-html --cov src/atomforge

ruff-check:
    uv run ruff check .

ruff-fmt:
    uv run ruff format .

# Default recipe - run all checks
default: test lint typecheck

# Run unit tests for all modules
test:
    uv run pytest modules/

# Run linter with ruff
lint:
    uv run ruff check .

# Run type checking with ty
typecheck:
    uv run ty check

# Format code with ruff
fmt:
    uv run ruff format .

# Fix linting issues automatically
fix:
    uv run ruff check --fix .

# Clean Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

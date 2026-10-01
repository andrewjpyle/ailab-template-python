.DEFAULT_GOAL := help
.PHONY: help install lint format test eval demo hooks scan docker-build docker-run clean

IMAGE  ?= ailab-template-python:local
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-13s %s\n", $$1, $$2}'

install: ## Create .venv from uv.lock (with dev tools)
	uv sync --locked

lint: ## Ruff lint + format check + mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

format: ## Auto-fix lint issues and format
	uv run ruff check --fix .
	uv run ruff format .

test: ## Run the test suite with coverage
	uv run pytest --cov --cov-report=term-missing

eval: ## Run the eval and enforce the regression gate
	uv run ailab-eval

demo: ## Classify a few samples, then run the eval
	uv run ailab-demo

hooks: ## Enable the repo's git hooks (required once per clone)
	git config core.hooksPath .githooks
	@echo "hooks enabled: .githooks/pre-push will run gitleaks + denylist scan"

scan: ## Secret scan: gitleaks over full history + denylist scan
	gitleaks git --no-banner --redact --config .gitleaks.toml .
	scripts/denylist_scan.sh

docker-build: ## Build the runtime image
	docker build --build-arg GIT_COMMIT=$(COMMIT) -t $(IMAGE) .

docker-run: ## Run the image (demo + eval)
	docker run --rm $(IMAGE)

clean: ## Remove caches and generated results
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov eval_results.json

# Run `make help` to see every command. All teammates use these, never ad-hoc commands.
.DEFAULT_GOAL := help
SHELL := /bin/bash

help: ## Show commands
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'

doctor: ## Check that your machine has the right tools
	@for t in docker git uv node npm; do command -v $$t >/dev/null && echo "ok   $$t" || echo "MISSING $$t"; done
	@docker compose version >/dev/null 2>&1 && echo "ok   docker compose" || echo "MISSING docker compose"
	@test -f .env && echo "ok   .env" || echo "MISSING .env (run: make setup)"

setup: ## First time: install all dependencies exactly as locked
	@test -f .env || cp .env.example .env
	cd services/brain && uv sync --frozen
	cd web && npm ci

up: ## Build and start everything (the judges' command)
	docker compose up --build -d --wait
	@echo "Web: http://localhost:3000   Brain API: http://localhost:8001/docs"

down: ## Stop everything
	docker compose down

logs: ## Follow logs
	docker compose logs -f --tail=100

reset: ## Stop and delete the database (fresh seed next time)
	docker compose down -v

test: ## Unit tests (brain + web)
	cd services/brain && uv run pytest
	cd web && npm test

lint: ## Linters and formatters in check mode
	cd services/brain && uv run ruff check . && uv run ruff format --check .
	cd web && npm run lint && npm run format:check

typecheck: ## Static types
	cd services/brain && uv run mypy
	cd web && npm run build

fmt: ## Auto-format code
	cd services/brain && uv run ruff format . && uv run ruff check --fix .
	cd web && npm run format

test-gateway: ## Integration test through the gateway (needs `make up`)
	cd services/brain && uv run pytest tests/test_gateway_live.py -p no:cacheprovider --no-cov

simulate: ## Simulated employees chat through the gateway so the dashboard moves (needs `make up`)
	docker compose --profile sim run --rm sim

validate: ## Check the team's data files (prompts, AI tools, org)
	cd services/brain && uv run python ../../scripts/validate_data.py

check: validate lint typecheck test ## Everything CI checks. Run before every commit.

e2e: ## End-to-end + accessibility (needs `make up` first)
	cd web && npx playwright install chromium && npm run e2e

eval: ## Detection quality report vs regex baseline, pass/fail against the targets (writes eval/report.md)
	cd services/brain && uv run python -m brain.eval.run

.PHONY: simulate test-gateway help doctor setup up down logs reset test lint typecheck fmt validate check e2e eval

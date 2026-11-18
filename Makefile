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
	@sh scripts/gen_hmac_key.sh
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

loadtest: ## Latency under concurrent load, p95 against the 100 ms target (needs `make up`)
	cd services/brain && uv run python ../../scripts/loadtest.py

local: ## Start the optional local model (Ollama, gemma3:1b; first start downloads about 1 GB)
	docker compose --profile local up -d --wait ollama

redteam: ## Attack the safety check with promptfoo cases and garak's known attack prompts (needs `make up`)
	uv run --project services/brain python scripts/redteam.py

injection-model: ## Download the optional prompt-injection classifier (about 740 MB) for the brain
	docker compose run --rm --no-deps -v $(PWD)/scripts:/scripts:ro --entrypoint python brain /scripts/get_injection_model.py

validate: ## Check the team's data files (prompts, AI tools, org)
	cd services/brain && uv run python ../../scripts/validate_data.py

check: validate lint typecheck test ## Everything CI checks. Run before every commit.

split-test: ## Split storage tests inside the containers (vaults start automatically)
	@sh scripts/gen_hmac_key.sh
	docker compose --profile test run --rm --build splitstore-tests

split-demo: ## Split storage demo: seed salaries, dump vault-a, aggregate, tamper
	@sh scripts/gen_hmac_key.sh
	docker compose run --rm brain python -m brain.splitstore.demo

e2e: ## End-to-end + accessibility (needs `make up` first)
	cd web && npx playwright install chromium && npm run e2e

siem: ## Start the demo SOC (syslog receiver) and follow the incidents arriving (X30; set SIEM_SYSLOG_HOST=syslog-receiver in .env first)
	docker compose --profile siem up -d syslog-receiver
	docker compose up -d brain
	docker compose logs -f --tail=20 syslog-receiver

calibrate: ## Sweep the paraphrase cutoff and write docs/calibration.md and .svg (X25)
	cd services/brain && uv run python ../../scripts/calibrate.py

eval: ## Detection quality report vs regex baseline, pass/fail against the targets (writes eval/report.md)
	cd services/brain && uv run python -m brain.eval.run

judge-data: ## Regenerate the judge fine-tune data from data/train_org (D7, deterministic, no dependencies)
	python3 scripts/gen_finetune.py

judge-ollama: ## Start the judge's own Ollama on port 11435 (separate from `make up`, which would remove a compose-started one)
	docker start judge-ollama 2>/dev/null || docker run -d --name judge-ollama --restart unless-stopped -p 11435:11434 -v data-dna_ollama:/root/.ollama -e OLLAMA_KEEP_ALIVE=30m ollama/ollama:0.40.16

judge-eval: ## Compare plain gemma3:1b (dna-local) with the tuned judge on the test set (needs `make judge-ollama` and the dna-judge model, see docs/JUDGE_FINETUNE.md)
	python3 scripts/eval_judge.py dna-judge dna-local --url http://localhost:11435 --out eval/judge_eval.md

.PHONY: siem judge-data judge-ollama judge-eval split-test split-demo calibrate injection-model redteam local loadtest simulate test-gateway help doctor setup up down logs reset test lint typecheck fmt validate check e2e eval

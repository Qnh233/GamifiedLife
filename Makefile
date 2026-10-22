# 统一评估入口：方便在本地和 CI 中直接调用。

.PHONY: help test test-unit test-integration test-e2e eval-routing eval-routing-golden eval-judge-planner eval-judge-chat eval-perf-smoke eval-perf-mock eval-all

PYTHON ?= python
BASE_URL ?= http://127.0.0.1:5000

help:
	@echo "Available targets:"
	@echo "  make test"
	@echo "  make test-unit"
	@echo "  make test-integration"
	@echo "  make test-e2e"
	@echo "  make eval-routing"
	@echo "  make eval-routing-golden"
	@echo "  make eval-judge-planner"
	@echo "  make eval-judge-chat"
	@echo "  make eval-perf-smoke"
	@echo "  make eval-perf-mock"
	@echo "  make eval-all"

test:
	$(PYTHON) -m pytest tests/unit tests/integration tests/e2e

test-unit:
	$(PYTHON) -m pytest tests/unit

test-integration:
	$(PYTHON) -m pytest tests/integration

test-e2e:
	$(PYTHON) -m pytest tests/e2e

eval-routing:
	$(PYTHON) evals/runners/run_supervisor_eval.py --mode dataset

eval-routing-golden:
	$(PYTHON) evals/runners/run_supervisor_eval.py --mode golden

eval-judge-planner:
	$(PYTHON) evals/runners/run_judge_eval.py --mode planner

eval-judge-chat:
	$(PYTHON) evals/runners/run_judge_eval.py --mode chat

eval-perf-smoke:
	$(PYTHON) evals/runners/run_perf_smoke.py --base-url $(BASE_URL)

eval-perf-mock:
	$(PYTHON) evals/runners/run_mock_workflow_perf.py

eval-all: test eval-routing eval-routing-golden eval-perf-mock

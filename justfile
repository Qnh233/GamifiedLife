# 统一评估命令入口，适合本地开发直接执行。

set shell := ["powershell", "-NoLogo", "-Command"]

python := "python"
base_url := "http://127.0.0.1:5000"

default:
    just --list

test:
    {{python}} -m pytest tests/unit tests/integration tests/e2e

test-unit:
    {{python}} -m pytest tests/unit

test-integration:
    {{python}} -m pytest tests/integration

test-e2e:
    {{python}} -m pytest tests/e2e

eval-routing:
    {{python}} evals/runners/run_supervisor_eval.py --mode dataset

eval-routing-golden:
    {{python}} evals/runners/run_supervisor_eval.py --mode golden

eval-judge-planner:
    {{python}} evals/runners/run_judge_eval.py --mode planner

eval-judge-chat:
    {{python}} evals/runners/run_judge_eval.py --mode chat

eval-perf-smoke:
    {{python}} evals/runners/run_perf_smoke.py --base-url {{base_url}}

eval-perf-mock:
    {{python}} evals/runners/run_mock_workflow_perf.py

eval-all:
    {{python}} -m pytest tests/unit tests/integration tests/e2e
    {{python}} evals/runners/run_supervisor_eval.py --mode dataset
    {{python}} evals/runners/run_supervisor_eval.py --mode golden
    {{python}} evals/runners/run_mock_workflow_perf.py

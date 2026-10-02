.DEFAULT_GOAL := help

PYTHON ?= python3
VENV ?= venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
DEPS_STAMP := $(VENV)/.synetra-analytics-deps
HOST ?= 127.0.0.1
PORT ?= 8000

.PHONY: help install run dev

help: ## Show the available analytics backend commands.
	@awk 'BEGIN {FS = ":.*## "; printf "Synetra analytics backend commands:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  make %-10s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(PY):
	$(PYTHON) -m venv "$(VENV)"

$(DEPS_STAMP): requirements.txt $(PY)
	$(PIP) install -r requirements.txt
	@touch "$(DEPS_STAMP)"

install: $(DEPS_STAMP) ## Install the analytics backend dependencies.

run: $(DEPS_STAMP) ## Install when needed, then run the analytics backend on port 8000.
	PYTHONPATH=. exec $(PY) -m uvicorn main:app --host "$(HOST)" --port "$(PORT)"

dev: $(DEPS_STAMP) ## Install when needed, then run with automatic reload.
	PYTHONPATH=. exec $(PY) -m uvicorn main:app --reload --host "$(HOST)" --port "$(PORT)"

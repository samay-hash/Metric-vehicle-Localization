.DEFAULT_GOAL := help

NPM ?= npm
HOST ?= 127.0.0.1
PORT ?= 5173
DEPS_STAMP := node_modules/.synetra-frontend-deps

.PHONY: help install dev build preview

help: ## Show the available frontend commands.
	@awk 'BEGIN {FS = ":.*## "; printf "Synetra frontend commands:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  make %-10s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(DEPS_STAMP): package.json package-lock.json
	$(NPM) ci
	@touch "$(DEPS_STAMP)"

install: $(DEPS_STAMP) ## Install the locked frontend dependencies.

dev: $(DEPS_STAMP) ## Install when needed, then run the Vite development server.
	$(NPM) run dev -- --host "$(HOST)" --port "$(PORT)"

build: $(DEPS_STAMP) ## Create a production frontend bundle.
	$(NPM) run build

preview: $(DEPS_STAMP) ## Preview the production bundle locally.
	$(NPM) run preview -- --host "$(HOST)" --port "$(PORT)"

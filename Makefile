.DEFAULT_GOAL := help

.PHONY: help backend registry frontend install-backend install-registry install-frontend registry-env registry-migrate registry-bootstrap registry-seed registry-seed-rbac registry-enrich

help: ## Show commands for each independently running service.
	@awk 'BEGIN {FS = ":.*## "; printf "Synetra services (run each service in its own terminal):\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  make %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

backend: ## Start the analytics backend at http://127.0.0.1:8000.
	$(MAKE) -C backend run

registry: ## Start the CCTV registry API at http://127.0.0.1:8001.
	$(MAKE) -C backend -f Makefile.registry run

frontend: ## Start the dashboard at http://127.0.0.1:5173.
	$(MAKE) -C frontend dev

install-backend: ## Install analytics backend dependencies.
	$(MAKE) -C backend install

install-registry: ## Install registry API dependencies.
	$(MAKE) -C backend -f Makefile.registry install

install-frontend: ## Install dashboard dependencies.
	$(MAKE) -C frontend install

registry-env: ## Create the registry environment file if needed.
	$(MAKE) -C backend -f Makefile.registry env

registry-migrate: ## Apply registry database migrations.
	$(MAKE) -C backend -f Makefile.registry migrate

registry-bootstrap: ## Import or refresh the configured Sentinel catalogue.
	$(MAKE) -C backend -f Makefile.registry bootstrap

registry-seed: ## Create the five local vendor accounts.
	$(MAKE) -C backend -f Makefile.registry seed

registry-seed-rbac: ## Create local dashboard accounts for each RBAC role.
	$(MAKE) -C backend -f Makefile.registry seed-rbac

registry-enrich: ## Fill missing Sentinel locations and approximate GIS coordinates.
	$(MAKE) -C backend -f Makefile.registry enrich

.PHONY: registry-health-worker
registry-health-worker: ## Run background RTSP health monitoring (requires FFmpeg).
	$(MAKE) -C backend -f Makefile.registry health-worker

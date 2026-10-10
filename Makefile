# ==============================================================================
# FeedbackPulse — Project Operations & Automation Makefile
# ==============================================================================
# Sourcing environment variables from cloud.env if present
-include cloud.env
export

# Ensure standard binary directories (including ~/.local/bin where uv resides) are in PATH
export PATH := $(HOME)/.local/bin:$(HOME)/.cargo/bin:/usr/local/bin:$(PATH)

# Resolve uv binary location automatically
UV ?= $(shell if [ -x "$$HOME/.local/bin/uv" ]; then echo "$$HOME/.local/bin/uv"; elif [ -x "$$HOME/.cargo/bin/uv" ]; then echo "$$HOME/.cargo/bin/uv"; else which uv 2>/dev/null || echo "uv"; fi)

.PHONY: help test lint portability-audit validate-config docker-build docker-push dry-run deploy status change-traffic verify-rollback

help:
	@echo "========================================================================"
	@echo "FeedbackPulse Operations & Automation"
	@echo "========================================================================"
	@echo "Development & Verification:"
	@echo "  make test               : Run pytest test suite"
	@echo "  make lint               : Run ruff check"
	@echo "  make portability-audit  : Run automated portability audit (P01-T03 §10)"
	@echo "  make validate-config    : Validate Container App template constraints"
	@echo "  make smoke-test         : Run public cloud API contract smoke tests (12 cases)"
	@echo "  make load-test          : Run k6 load & concurrency benchmark (VUs=2, p95 <= 3s)"
	@echo "  make verify-rollback    : Verify rollback traffic shift and test live endpoint"
	@echo ""
	@echo "Container & Image Operations:"
	@echo "  make docker-build       : Build Docker container image locally"
	@echo "  make docker-push        : Login to ACR and push container image"
	@echo ""
	@echo "Cloud Deployment & Management (Azure Container Apps):"
	@echo "  make dry-run            : Dry run provisioning and validate cloud environment"
	@echo "  make deploy             : Deploy or update Azure Container App from YAML"
	@echo "  make status             : Check deployed Container App FQDN and revisions"
	@echo "  make change-traffic REV=...   : Shift 100% traffic back to specified revision"
	@echo "========================================================================"

# --- Testing & Quality Assurance ---
test:
	$(UV) run pytest

lint:
	$(UV) run ruff check

portability-audit:
	$(UV) run pytest tests/test_portability.py -v

validate-config:
	$(UV) run python cloudlayer/render_config.py --validate-only

smoke-test:
	PYTHONPATH=src $(UV) run python scripts/cloud_check.py

load-test:
	k6 run -e TARGET="https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io/predict" -e TOKEN="$(SERVICE_TOKEN)" -e VUS=2 -e DURATION=10s loadtest/k6.js

# --- Docker Container Operations ---
docker-build:
	docker build --platform linux/amd64 -t $(IMAGE_TAG) .

docker-push:
	@if [ -z "$(AZURE_REGISTRY_NAME)" ]; then echo "Error: AZURE_REGISTRY_NAME is not set in cloud.env"; exit 1; fi
	az acr login --name $(AZURE_REGISTRY_NAME)
	docker push $(IMAGE_TAG)

# --- Cloud Deployment & Lifecycle Operations ---
dry-run: validate-config
	@echo "Checking Azure authentication..."
	@az account show --query "{Subscription:name, User:user.name}" -o json
	@echo "Checking Managed Environment '$(AZURE_CONTAINER_APP_ENV)' in '$(AZURE_RESOURCE_GROUP)'..."
	@MANAGED_ENV_ID=$$(az containerapp env show -n $(AZURE_CONTAINER_APP_ENV) -g $(AZURE_RESOURCE_GROUP) --query id -o tsv) && \
		echo "Found Managed Environment ID: $$MANAGED_ENV_ID"
	@echo "Checking ACR '$(AZURE_REGISTRY_NAME)'..."
	@az acr show -n $(AZURE_REGISTRY_NAME) -g $(AZURE_RESOURCE_GROUP) --query "{LoginServer:loginServer, SKU:sku.name}" -o json
	@echo "==> Dry run successful: Cloud environment and template constraints verified."

deploy: validate-config
	@set -e; \
	if [ -z "$(AZURE_CONTAINER_APP_NAME)" ] || [ -z "$(AZURE_RESOURCE_GROUP)" ]; then \
		echo "Error: AZURE_CONTAINER_APP_NAME and AZURE_RESOURCE_GROUP must be set in cloud.env"; exit 1; \
	fi; \
	echo "Resolving Azure Environment & Registry credentials..."; \
	MANAGED_ENV_ID=$$(az containerapp env show -n $(AZURE_CONTAINER_APP_ENV) -g $(AZURE_RESOURCE_GROUP) --query id -o tsv); \
	REG_PASS=$$(az acr credential show -n $(AZURE_REGISTRY_NAME) --query "passwords[0].value" -o tsv); \
	TEMP_YAML=$$(mktemp cloudlayer/containerapp.render.XXXXXX.yaml); \
	trap 'rm -f "$$TEMP_YAML"' EXIT INT TERM; \
	MANAGED_ENV_ID="$$MANAGED_ENV_ID" \
	REGISTRY_PASSWORD="$$REG_PASS" \
	REGISTRY_SERVER="$(AZURE_REGISTRY_SERVER)" \
	REGISTRY_USERNAME="$(AZURE_REGISTRY_NAME)" \
	$(UV) run python cloudlayer/render_config.py --output "$$TEMP_YAML"; \
	if az containerapp show -n $(AZURE_CONTAINER_APP_NAME) -g $(AZURE_RESOURCE_GROUP) >/dev/null 2>&1; then \
		echo "Updating existing Container App '$(AZURE_CONTAINER_APP_NAME)'..."; \
		az containerapp update -n $(AZURE_CONTAINER_APP_NAME) -g $(AZURE_RESOURCE_GROUP) --yaml "$$TEMP_YAML"; \
	else \
		echo "Creating new Container App '$(AZURE_CONTAINER_APP_NAME)'..."; \
		az containerapp create -n $(AZURE_CONTAINER_APP_NAME) -g $(AZURE_RESOURCE_GROUP) --environment $(AZURE_CONTAINER_APP_ENV) --yaml "$$TEMP_YAML"; \
	fi; \
	echo "==> Deployment complete. Run 'make status' to check endpoints."

status:
	@if [ -z "$(AZURE_CONTAINER_APP_NAME)" ] || [ -z "$(AZURE_RESOURCE_GROUP)" ]; then \
		echo "Error: AZURE_CONTAINER_APP_NAME and AZURE_RESOURCE_GROUP must be set in cloud.env"; exit 1; \
	fi
	az containerapp show -n $(AZURE_CONTAINER_APP_NAME) -g $(AZURE_RESOURCE_GROUP) \
		--query "{FQDN:properties.configuration.ingress.fqdn, Traffic:properties.configuration.ingress.traffic, RevisionsMode:properties.configuration.activeRevisionsMode}" -o json

change-traffic:
	@if [ -z "$(REV)" ]; then \
		echo "Error: Must specify revision name to change traffic. Example: make change-traffic REV=feedbackpulse-api--0001"; exit 1; \
	fi
	@if [ -z "$(AZURE_CONTAINER_APP_NAME)" ] || [ -z "$(AZURE_RESOURCE_GROUP)" ]; then \
		echo "Error: AZURE_CONTAINER_APP_NAME and AZURE_RESOURCE_GROUP must be set in cloud.env"; exit 1; \
	fi
	az containerapp ingress traffic set -n $(AZURE_CONTAINER_APP_NAME) -g $(AZURE_RESOURCE_GROUP) --revision-weight $(REV)=100

verify-rollback:
	PYTHONPATH=src $(UV) run python scripts/verify_rollback.py $(if $(SIMULATE),--simulate-new-first,) $(ARGS)

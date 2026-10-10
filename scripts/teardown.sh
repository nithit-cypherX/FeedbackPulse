#!/usr/bin/env bash
# ==============================================================================
# FeedbackPulse — Cloud Resources Teardown Script (P04-T06)
# ==============================================================================
# Safely tears down deployed cloud resources on Azure to avoid unexpected
# costs on student subscription.
#
# SAFEGUARD POLICY:
# By default, this script operates in SAFE mode (--app-only):
# It deletes ONLY the Container App ('feedbackpulse-api' and its revisions).
# It preserves the Azure Container Registry (ACR) and Container Apps Environment
# so that simply pushing new code via 'git push' can automatically recreate
# and redeploy the service via the GitHub Actions CD pipeline.
#
# Interactive confirmation is ALWAYS required: the user must explicitly
# type 'yes' to proceed with deletion.
#
# Base infrastructure teardown (ACR and Environment) is commented out by default
# to prevent accidental destruction. To permanently destroy all resources,
# uncomment the marked sections below.
#
# Supported modes:
#   make teardown-dry-run               # Preview commands without executing
#   make teardown                       # Interactive deletion of Container App
# ==============================================================================

set -euo pipefail

# ANSI color codes
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

# Load environment configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${ROOT_DIR}/cloud.env" ]]; then
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/cloud.env"
fi

# Configuration with fallback defaults
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-itcs355-6688166}"
CONTAINER_APP_NAME="${AZURE_CONTAINER_APP_NAME:-feedbackpulse-api}"
CONTAINER_APP_ENV="${AZURE_CONTAINER_APP_ENV:-itcs355-env}"
REGISTRY_NAME="${AZURE_REGISTRY_NAME:-itcs3556688166}"

# Operational flags
DRY_RUN=false
# Default scope is locked to 'app-only' for safety
SCOPE="app-only"

usage() {
    cat <<EOF
${BOLD}FeedbackPulse Teardown Utility${NC}
Safely cleans up cloud infrastructure deployed on Azure.

${BOLD}Usage:${NC}
  $0 [options]

${BOLD}Options:${NC}
  -n, --dry-run       Preview commands and resources that would be deleted (no action taken)
  --app-only          Delete only the Container App (default safe mode; preserves ACR & Env)
  -h, --help          Show this help message and exit

${BOLD}Examples:${NC}
  $0 --dry-run
  $0
EOF
    exit 0
}

# Parse CLI options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        --app-only)
            SCOPE="app-only"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

echo -e "${BOLD}${CYAN}========================================================================${NC}"
echo -e "${BOLD}${CYAN}FeedbackPulse — Azure Cloud Teardown Verification (P04-T06)${NC}"
echo -e "${BOLD}${CYAN}========================================================================${NC}"
echo -e "Resource Group : ${BOLD}${RESOURCE_GROUP}${NC}"
echo -e "Scope Mode     : ${BOLD}${SCOPE} (Safe Mode: Container App only)${NC}"
echo -e "Dry Run Mode   : ${BOLD}${DRY_RUN}${NC}"
echo ""

# Verify Azure CLI availability
if ! command -v az &>/dev/null; then
    echo -e "${RED}Error: Azure CLI ('az') is not installed or not in PATH.${NC}"
    exit 1
fi

# Verify Azure CLI login
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Azure CLI is not logged in. Run 'az login' first.${NC}"
    exit 1
fi

CURRENT_SUB="$(az account show --query "name" -o tsv 2>/dev/null || echo "Unknown")"
echo -e "Active Azure Subscription: ${BOLD}${CURRENT_SUB}${NC}"
echo ""

# Plan resources to delete based on scope
RESOURCES_TO_DELETE=()
RESOURCES_TO_DELETE+=("Container App: ${CONTAINER_APP_NAME} (in RG ${RESOURCE_GROUP})")

# -----------------------------------------------------------------------------
# SAFEGUARD: To include base infrastructure in deletion, uncomment below:
# -----------------------------------------------------------------------------
# RESOURCES_TO_DELETE+=("Container App Environment: ${CONTAINER_APP_ENV} (in RG ${RESOURCE_GROUP})")
# RESOURCES_TO_DELETE+=("Container Registry: ${REGISTRY_NAME} (in RG ${RESOURCE_GROUP})")
# -----------------------------------------------------------------------------

echo -e "${BOLD}Target resources planned for deletion:${NC}"
for res in "${RESOURCES_TO_DELETE[@]}"; do
    echo -e "  • ${YELLOW}${res}${NC}"
done
echo ""

if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BOLD}${GREEN}[DRY RUN] Simulation complete. The following CLI commands would be run:${NC}"
    echo -e "  ${CYAN}az containerapp delete -n ${CONTAINER_APP_NAME} -g ${RESOURCE_GROUP} --yes${NC}"
    
    # -------------------------------------------------------------------------
    # SAFEGUARD: Uncomment below if simulating base infrastructure deletion:
    # -------------------------------------------------------------------------
    # echo -e "  ${CYAN}az containerapp env delete -n ${CONTAINER_APP_ENV} -g ${RESOURCE_GROUP} --yes${NC}"
    # echo -e "  ${CYAN}az acr delete -n ${REGISTRY_NAME} -g ${RESOURCE_GROUP} --yes${NC}"
    # -------------------------------------------------------------------------

    echo ""
    echo -e "${GREEN}[DRY RUN] No cloud resources were modified or removed.${NC}"
    exit 0
fi

# Prompt confirmation (Always required for safety)
echo -e "${YELLOW}${BOLD}WARNING: You are about to permanently delete the Container App '${CONTAINER_APP_NAME}'!${NC}"
read -r -p "Are you sure you want to proceed? (yes/N): " CONFIRMATION
if [[ "$CONFIRMATION" != "yes" && "$CONFIRMATION" != "YES" ]]; then
    echo -e "${YELLOW}Teardown cancelled by user. No resources were modified.${NC}"
    exit 0
fi

# Execution phase
echo ""
echo -e "${BOLD}Executing resource deletion...${NC}"

# 1. Delete Container App (Active)
if az containerapp show -n "${CONTAINER_APP_NAME}" -g "${RESOURCE_GROUP}" &>/dev/null; then
    echo -e "Deleting Container App '${CONTAINER_APP_NAME}'..."
    az containerapp delete -n "${CONTAINER_APP_NAME}" -g "${RESOURCE_GROUP}" --yes
    echo -e "${GREEN}[OK] Container App '${CONTAINER_APP_NAME}' deleted.${NC}"
else
    echo -e "${YELLOW}[SKIP] Container App '${CONTAINER_APP_NAME}' does not exist.${NC}"
fi

# =============================================================================
# SAFEGUARD: The following sections for Environment and ACR deletion are
# commented out by default. This ensures base infrastructure remains intact
# and allows 'git push' to recreate the Container App automatically via CD.
#
# To permanently delete Environment and ACR at project conclusion, uncomment:
# =============================================================================
# if az containerapp env show -n "${CONTAINER_APP_ENV}" -g "${RESOURCE_GROUP}" &>/dev/null; then
#     echo -e "Deleting Container App Environment '${CONTAINER_APP_ENV}'..."
#     az containerapp env delete -n "${CONTAINER_APP_ENV}" -g "${RESOURCE_GROUP}" --yes
#     echo -e "${GREEN}[OK] Container App Environment '${CONTAINER_APP_ENV}' deleted.${NC}"
# else
#     echo -e "${YELLOW}[SKIP] Container App Environment '${CONTAINER_APP_ENV}' does not exist.${NC}"
# fi
#
# if az acr show -n "${REGISTRY_NAME}" -g "${RESOURCE_GROUP}" &>/dev/null; then
#     echo -e "Deleting Container Registry '${REGISTRY_NAME}'..."
#     az acr delete -n "${REGISTRY_NAME}" -g "${RESOURCE_GROUP}" --yes
#     echo -e "${GREEN}[OK] Container Registry '${REGISTRY_NAME}' deleted.${NC}"
# else
#     echo -e "${YELLOW}[SKIP] Container Registry '${REGISTRY_NAME}' does not exist.${NC}"
# fi
# =============================================================================

echo ""
echo -e "${BOLD}${GREEN}========================================================================${NC}"
echo -e "${BOLD}${GREEN}Teardown completed successfully! Container App removed.${NC}"
echo -e "${CYAN}Note: ACR & Environment were preserved. A new 'git push' will automatically recreate the app.${NC}"
echo -e "${BOLD}${GREEN}========================================================================${NC}"

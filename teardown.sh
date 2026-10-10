#!/usr/bin/env bash
# Entrypoint for FeedbackPulse Cloud Teardown
exec "$(dirname "$0")/scripts/teardown.sh" "$@"

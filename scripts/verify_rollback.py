#!/usr/bin/env python3
"""Automated Rollback Verification Script for FeedbackPulse (P04-T05).

Verifies the Azure Container Apps native rollback mechanism:
1. Discovers deployed revisions and orders them chronologically to identify:
   - New / Current Revision (e.g. feedbackpulse-api--rev2)
   - Previous Stable Revision (e.g. feedbackpulse-api--2zaws5o)
2. Executes rollback by shifting 100% traffic back to the Previous Stable Revision.
3. Handles scale-to-zero wake-up via readiness polling.
4. Verifies live API endpoints (/health, /ready, /predict) on the rolled-back revision.
5. Records structured evidence to reports/P04-rollback-evidence.json.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

DEFAULT_APP_NAME = os.getenv("AZURE_CONTAINER_APP_NAME", "feedbackpulse-api")
DEFAULT_RG = os.getenv("AZURE_RESOURCE_GROUP", "itcs355-6688166")
DEFAULT_ENDPOINT = os.getenv(
    "TARGET",
    "https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io",
).rstrip("/")
DEFAULT_TOKEN = os.getenv("SERVICE_TOKEN", "test-service-token-secret-12345")


def get_containerapp_ingress(app_name: str, rg: str) -> dict[str, Any]:
    """Retrieve current ingress configuration and traffic weights."""
    cmd = [
        "az",
        "containerapp",
        "show",
        "-n",
        app_name,
        "-g",
        rg,
        "--query",
        "properties.configuration.ingress",
        "-o",
        "json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def get_containerapp_revisions(app_name: str, rg: str) -> list[dict[str, Any]]:
    """Retrieve all revisions and their provisioning/health states."""
    cmd = [
        "az",
        "containerapp",
        "revision",
        "list",
        "-n",
        app_name,
        "-g",
        rg,
        "-o",
        "json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def shift_traffic(app_name: str, rg: str, revision_name: str, weight: int = 100) -> None:
    """Shift traffic weight to a designated revision."""
    cmd = [
        "az",
        "containerapp",
        "ingress",
        "traffic",
        "set",
        "-n",
        app_name,
        "-g",
        rg,
        "--revision-weight",
        f"{revision_name}={weight}",
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def verify_live_endpoint(endpoint: str, token: str) -> dict[str, Any]:
    """Verify live endpoint functionality after rollback, handling cold-starts safely."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(verify=False, timeout=60.0) as client:
        # Polling readiness probe to ensure scaled-to-zero replicas are fully awake and ready
        print("Waiting for rolled-back revision to become ready (handling cold start)...")
        t_poll = time.perf_counter()
        for attempt in range(1, 25):
            try:
                probe = client.get(f"{endpoint}/ready", timeout=5.0)
                if probe.status_code == 200:
                    print(f"Service ready in {time.perf_counter() - t_poll:.2f}s (attempt {attempt}). Proceeding with checks...\n")
                    break
            except Exception:  # noqa: BLE001
                time.sleep(2)
        else:
            print(f"Warning: Readiness polling finished after {time.perf_counter() - t_poll:.2f}s.\n")

        # Check /health
        t0 = time.perf_counter()
        r_health = client.get(f"{endpoint}/health", timeout=15.0)
        lat_health = (time.perf_counter() - t0) * 1000.0

        # Check /ready
        t0 = time.perf_counter()
        r_ready = client.get(f"{endpoint}/ready", timeout=15.0)
        lat_ready = (time.perf_counter() - t0) * 1000.0

        # Check /predict
        sample_payload = {"text": "Excellent service and punctual flight arrival!"}
        t0 = time.perf_counter()
        r_predict = client.post(f"{endpoint}/predict", headers=headers, json=sample_payload, timeout=30.0)
        lat_predict = (time.perf_counter() - t0) * 1000.0

    return {
        "health": {
            "status_code": r_health.status_code,
            "latency_ms": round(lat_health, 2),
            "body": r_health.json(),
        },
        "ready": {
            "status_code": r_ready.status_code,
            "latency_ms": round(lat_ready, 2),
            "body": r_ready.json(),
        },
        "predict": {
            "status_code": r_predict.status_code,
            "latency_ms": round(lat_predict, 2),
            "body": r_predict.json(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Azure Container Apps Native Rollback")
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME)
    parser.add_argument("--resource-group", default=DEFAULT_RG)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    parser.add_argument("--target-rev", help="Specific target revision to rollback to")
    parser.add_argument(
        "--simulate-new-first",
        action="store_true",
        help="Simulate new version active first (100%% to latest) before triggering rollback",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/P04-rollback-evidence.json"),
        help="Evidence output path",
    )
    args = parser.parse_args()

    print("=" * 80)
    print(f"FeedbackPulse Rollback Verification: {args.app_name} in {args.resource_group}")
    print("=" * 80)

    # 1. Discover and order revisions chronologically
    revisions = get_containerapp_revisions(args.app_name, args.resource_group)
    if not revisions:
        print("Error: No revisions found for container app.")
        return 1

    parsed_revs = []
    for rev in revisions:
        props = rev.get("properties", {})
        name = rev.get("name")
        active = props.get("active") if "active" in props else rev.get("active")
        traffic = props.get("trafficWeight") if "trafficWeight" in props else rev.get("trafficWeight", 0)
        state = props.get("provisioningState") if "provisioningState" in props else rev.get("provisioningState")
        created = props.get("createdTime") if "createdTime" in props else rev.get("createdTime", "")
        parsed_revs.append({
            "name": name,
            "createdTime": created,
            "active": active,
            "trafficWeight": traffic,
            "provisioningState": state,
        })

    # Sort revisions chronologically: index 0 is oldest, index -1 is newest
    chronological_revs = sorted(parsed_revs, key=lambda r: str(r.get("createdTime", "")))
    latest_rev = chronological_revs[-1]["name"]
    previous_stable_rev = chronological_revs[0]["name"] if len(chronological_revs) > 1 else latest_rev

    print("Discovered revisions (ordered chronologically):")
    for idx, r in enumerate(chronological_revs, start=1):
        role_label = "[PREVIOUS STABLE]" if r["name"] == previous_stable_rev else "[NEW / LATEST]"
        print(f"  {idx}. {role_label} {r['name']} (Created: {r['createdTime']}, Traffic: {r['trafficWeight']}%, State: {r['provisioningState']})")

    # 2. Check current traffic state
    ingress_before = get_containerapp_ingress(args.app_name, args.resource_group)
    traffic_before = ingress_before.get("traffic", [])

    # If --simulate-new-first requested, ensure we start on the latest revision
    if args.simulate_new_first and latest_rev != previous_stable_rev:
        print(f"\n[Scenario Setup] Simulating incident on new version: setting traffic 100% -> {latest_rev}...")
        shift_traffic(args.app_name, args.resource_group, latest_rev, 100)
        time.sleep(2)
        ingress_before = get_containerapp_ingress(args.app_name, args.resource_group)
        traffic_before = ingress_before.get("traffic", [])

    # 3. Determine target rollback revision
    # Rollback destination: Previous Stable Revision (or user-specified --target-rev)
    target_rev = args.target_rev or previous_stable_rev

    print("\nRollback Execution Plan:")
    print(f"  • Current Traffic Ingress     : {traffic_before}")
    print(f"  • Target Rollback Destination : {target_rev} (Previous Stable Revision)")

    # 4. Execute Rollback (Shift 100% traffic back to previous stable revision)
    print(f"\nExecuting Rollback: Shifting 100% traffic back to {target_rev}...")
    t0 = time.perf_counter()
    shift_traffic(args.app_name, args.resource_group, target_rev, 100)
    shift_duration_s = time.perf_counter() - t0
    print(f"[OK] Traffic successfully rolled back in {shift_duration_s:.2f} seconds.")

    # 5. Confirm post-rollback traffic distribution
    ingress_after = get_containerapp_ingress(args.app_name, args.resource_group)
    traffic_after = ingress_after.get("traffic", [])
    print(f"Post-Rollback Traffic Distribution: {traffic_after}")

    # 6. Verify live endpoint on the rolled-back revision
    print(f"\nVerifying live endpoint health on rolled-back revision at {args.endpoint}...")
    endpoint_verification = verify_live_endpoint(args.endpoint, args.token)
    h_ok = endpoint_verification["health"]["status_code"] == 200
    r_ok = endpoint_verification["ready"]["status_code"] == 200
    p_ok = endpoint_verification["predict"]["status_code"] == 200

    print(f"  • GET  /health  : status={endpoint_verification['health']['status_code']} ({endpoint_verification['health']['latency_ms']}ms)")
    print(f"  • GET  /ready   : status={endpoint_verification['ready']['status_code']} ({endpoint_verification['ready']['latency_ms']}ms)")
    print(f"  • POST /predict : status={endpoint_verification['predict']['status_code']} ({endpoint_verification['predict']['latency_ms']}ms) -> {endpoint_verification['predict']['body'].get('sentiment')}")

    passed = h_ok and r_ok and p_ok
    status_label = "ALL PASSED [OK]" if passed else "FAILED [X]"

    print("=" * 80)
    print(f"Rollback Verification Summary: {status_label}")
    print("=" * 80 + "\n")

    evidence_data: dict[str, Any] = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "container_app": args.app_name,
        "resource_group": args.resource_group,
        "endpoint": args.endpoint,
        "newest_revision": latest_rev,
        "previous_stable_revision": previous_stable_rev,
        "rollback_target_revision": target_rev,
        "revisions": [
            {
                "name": r.get("name"),
                "createdTime": r.get("createdTime"),
                "active": r.get("active"),
                "trafficWeight": r.get("trafficWeight"),
                "provisioningState": r.get("provisioningState"),
            }
            for r in chronological_revs
        ],
        "traffic_before": traffic_before,
        "traffic_after": traffic_after,
        "shift_duration_seconds": round(shift_duration_s, 2),
        "endpoint_verification": endpoint_verification,
        "status": "PASSED" if passed else "FAILED",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence_data, indent=2), encoding="utf-8")
    print(f"Rollback evidence saved to {args.output}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

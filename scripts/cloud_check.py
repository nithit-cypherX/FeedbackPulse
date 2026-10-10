#!/usr/bin/env python3
"""Cloud Smoke Test and API Contract Checker for FeedbackPulse.

Directly verifies P04-T04 criteria:
1. Public cloud HTTPS API contract verification on Azure Container Apps.
2. Checks 12 conditions: /health (200), /ready (200), 401 (auth missing/invalid),
   400 (malformed JSON), 422 (empty/missing text, 511 tokens limit),
   200 (510 tokens boundary), and sentiment classification quality (pos/neg/neu).
3. Saves verification evidence into reports/P04-cloud-check.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

DEFAULT_ENDPOINT = os.getenv(
    "TARGET",
    "https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io",
).rstrip("/")
DEFAULT_TOKEN = os.getenv("TOKEN", "test-service-token-secret-12345")


@dataclass
class CheckResult:
    test_name: str
    expected_status: int
    actual_status: int
    passed: bool
    latency_ms: float
    details: str


@dataclass
class SuiteRunResult:
    results: list[CheckResult]
    cold_start_seconds: float


def generate_boundary_texts() -> tuple[str, str]:
    """Generate exact 510-token (accepted) and 511-token (rejected) strings."""
    try:
        from feedbackpulse.inference import SentimentClassifier

        classifier = SentimentClassifier.load(
            "artifacts/sentiment-6e7ff9fbc17c/model",
            "sentiment-6e7ff9fbc17c-0110c462",
        )
        tokenizer = classifier._tokenizer
        token_id = tokenizer.encode(" good", add_special_tokens=False)[0]
        text_510 = tokenizer.decode([token_id] * 510)
        text_511 = tokenizer.decode([token_id] * 511)
        return text_510, text_511
    except Exception:  # noqa: BLE001
        token_word = " good"
        return token_word * 510, token_word * 511


async def run_cloud_checks(endpoint: str, token: str) -> SuiteRunResult:
    """Execute end-to-end API contract check against cloud endpoint."""
    print("=" * 80)
    print(f"FeedbackPulse Cloud Contract Check: {endpoint}")
    print("=" * 80)

    results: list[CheckResult] = []
    text_510, text_511 = generate_boundary_texts()

    headers_auth = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    headers_no_auth = {"Content-Type": "application/json"}
    headers_bad_auth = {
        "Authorization": "Bearer invalid-token-xyz-999",
        "Content-Type": "application/json",
    }

    cold_start_seconds = 0.0
    async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
        # Pre-flight check: measure readiness latency / cold start from 0 replicas
        print("Checking service readiness and measuring cold-start response...")
        t_poll_start = time.perf_counter()
        for attempt in range(1, 20):
            try:
                probe = await client.get(f"{endpoint}/ready", timeout=5.0)
                if probe.status_code == 200:
                    cold_start_seconds = time.perf_counter() - t_poll_start
                    print(f"Service ready in {cold_start_seconds:.2f}s (attempt {attempt}). Proceeding with checks...\n")
                    break
            except Exception:  # noqa: BLE001
                await asyncio.sleep(2)
        else:
            cold_start_seconds = time.perf_counter() - t_poll_start
        t0 = time.perf_counter()
        r = await client.get(f"{endpoint}/health")
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 200 and r.json().get("status") == "healthy"
        results.append(
            CheckResult(
                test_name="GET /health (Liveness Probe)",
                expected_status=200,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Body: {r.text[:60]}",
            )
        )

        # 2. Ready Probe
        t0 = time.perf_counter()
        r = await client.get(f"{endpoint}/ready")
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 200 and r.json().get("status") == "ready"
        results.append(
            CheckResult(
                test_name="GET /ready (Readiness Probe)",
                expected_status=200,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Model version: {r.json().get('model_version')}",
            )
        )

        # 3. Auth missing (401)
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_no_auth, json={"text": "hello"})
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 401 and r.json().get("error", {}).get("code") == "UNAUTHORIZED"
        results.append(
            CheckResult(
                test_name="POST /predict (Missing Token -> 401)",
                expected_status=401,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Code: {r.json().get('error', {}).get('code')}",
            )
        )

        # 4. Auth invalid (401)
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_bad_auth, json={"text": "hello"})
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 401 and r.json().get("error", {}).get("code") == "UNAUTHORIZED"
        results.append(
            CheckResult(
                test_name="POST /predict (Invalid Token -> 401)",
                expected_status=401,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Code: {r.json().get('error', {}).get('code')}",
            )
        )

        # 5. Malformed JSON (400)
        t0 = time.perf_counter()
        r = await client.post(
            f"{endpoint}/predict",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            content=b"this is invalid { json",
        )
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 400 and r.json().get("error", {}).get("code") == "BAD_REQUEST"
        results.append(
            CheckResult(
                test_name="POST /predict (Malformed JSON -> 400)",
                expected_status=400,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Code: {r.json().get('error', {}).get('code')}",
            )
        )

        # 6. Missing text field (422)
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_auth, json={"wrong": "field"})
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 422 and r.json().get("error", {}).get("code") == "INVALID_TEXT"
        results.append(
            CheckResult(
                test_name="POST /predict (Missing text field -> 422)",
                expected_status=422,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Code: {r.json().get('error', {}).get('code')}",
            )
        )

        # 7. Empty text string (422)
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_auth, json={"text": "   "})
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 422 and r.json().get("error", {}).get("code") == "INVALID_TEXT"
        results.append(
            CheckResult(
                test_name="POST /predict (Empty text string -> 422)",
                expected_status=422,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Code: {r.json().get('error', {}).get('code')}",
            )
        )

        # 8. Boundary: Exactly 510 tokens (200 accepted)
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_auth, json={"text": text_510})
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 200 and "sentiment" in r.json()
        results.append(
            CheckResult(
                test_name="POST /predict (Boundary: Exactly 510 tokens -> 200 OK)",
                expected_status=200,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Sentiment: {r.json().get('sentiment', 'N/A')}",
            )
        )

        # 9. Boundary: Exactly 511 tokens (422 TEXT_TOO_LONG)
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_auth, json={"text": text_511})
        lat = (time.perf_counter() - t0) * 1000.0
        passed = r.status_code == 422 and r.json().get("error", {}).get("code") == "TEXT_TOO_LONG"
        results.append(
            CheckResult(
                test_name="POST /predict (Boundary: 511 tokens -> 422 TEXT_TOO_LONG)",
                expected_status=422,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Code: {r.json().get('error', {}).get('code')}",
            )
        )

        # 10. Sentiment Quality: Positive
        pos_text = "The flight was wonderfully smooth and cabin crew was courteous and helpful!"
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_auth, json={"text": pos_text})
        lat = (time.perf_counter() - t0) * 1000.0
        data = r.json()
        passed = r.status_code == 200 and data.get("sentiment") == "positive"
        results.append(
            CheckResult(
                test_name="POST /predict (Known Positive Feedback)",
                expected_status=200,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Sentiment: {data.get('sentiment')}, Score: {data.get('score')}",
            )
        )

        # 11. Sentiment Quality: Negative
        neg_text = "Terrible experience, flight was canceled without refund and luggage was lost!"
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_auth, json={"text": neg_text})
        lat = (time.perf_counter() - t0) * 1000.0
        data = r.json()
        passed = r.status_code == 200 and data.get("sentiment") == "negative"
        results.append(
            CheckResult(
                test_name="POST /predict (Known Negative Feedback)",
                expected_status=200,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Sentiment: {data.get('sentiment')}, Score: {data.get('score')}",
            )
        )

        # 12. Sentiment Quality: Neutral
        neu_text = "The flight departed at 3:15 PM and arrived at gate 14 as scheduled."
        t0 = time.perf_counter()
        r = await client.post(f"{endpoint}/predict", headers=headers_auth, json={"text": neu_text})
        lat = (time.perf_counter() - t0) * 1000.0
        data = r.json()
        passed = r.status_code == 200 and data.get("sentiment") == "neutral"
        results.append(
            CheckResult(
                test_name="POST /predict (Known Neutral Feedback)",
                expected_status=200,
                actual_status=r.status_code,
                passed=passed,
                latency_ms=round(lat, 2),
                details=f"Sentiment: {data.get('sentiment')}, Score: {data.get('score')}",
            )
        )

    for res in results:
        status_symbol = "PASS [OK]" if res.passed else "FAIL [X]"
        print(f"[{status_symbol}] {res.test_name} ({res.latency_ms:.1f}ms)")
        print(f"       Status: {res.actual_status} (Expected: {res.expected_status}) | {res.details}")

    all_passed = all(res.passed for res in results)
    summary_status = "ALL PASSED" if all_passed else "FAILURES DETECTED"
    print("-" * 80)
    print(f"Cloud Check Summary: {sum(r.passed for r in results)}/{len(results)} passed ({summary_status}).")
    print("=" * 80 + "\n")
    return SuiteRunResult(results=results, cold_start_seconds=cold_start_seconds)


async def main_async() -> int:
    parser = argparse.ArgumentParser(description="FeedbackPulse Cloud Contract Check")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Cloud API endpoint URL")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer authorization service token")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/P04-cloud-check.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    suite = await run_cloud_checks(args.endpoint, args.token)
    results = suite.results
    cold_start_seconds = suite.cold_start_seconds

    total_checks = len(results)
    passed_checks = sum(r.passed for r in results)
    failed_checks = total_checks - passed_checks
    all_passed = failed_checks == 0 and total_checks > 0
    error_rate_pct = (failed_checks / total_checks * 100.0) if total_checks > 0 else 0.0

    print("=" * 80)
    print("PROPOSAL POINT 3 SLA METRICS BREAKDOWN (SMOKE & CONTRACT CHECK)")
    print("=" * 80)
    print(f"• Contract Error Rate        : {error_rate_pct:.2f}% (Target: 0.00% / < 1.0%) -> {'PASSED [OK]' if error_rate_pct == 0 else 'FAILED [X]'}")
    print(f"• Cold-Start Readiness Time   : {cold_start_seconds:.2f} s (Measured separately per Proposal §3)")
    print(f"• Contract Checks Status      : {passed_checks}/{total_checks} Passed -> {'ALL PASSED [OK]' if all_passed else 'FAILED [X]'}")
    print("=" * 80 + "\n")

    output_data: dict[str, Any] = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint": args.endpoint,
        "metrics_summary": {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "error_rate_pct": round(error_rate_pct, 2),
            "cold_start_seconds": round(cold_start_seconds, 2),
            "status": "PASSED" if all_passed else "FAILED",
            "reporting_policy": "Error rates and cold-start time are reported separately per Proposal §3",
        },
        "results": [asdict(r) for r in results],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(f"Cloud check results recorded to {args.output}")

    return 0 if all_passed else 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())

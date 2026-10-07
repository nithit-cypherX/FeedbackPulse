"""Measure how much memory and time loading the model costs.

P01-T03 section 5 requires these numbers before anyone sizes a container, and
P01-T03 section 12 leaves CPU and RAM undecided until they exist.

Each sample runs in a fresh process. Loading twice inside one process reuses a
warm allocator and already-mapped files, which would report a load far cheaper
than the first one a container ever does.

Run with:  PYTHONPATH=src uv run python -m feedbackpulse.measure
            PYTHONPATH=src uv run python -m feedbackpulse.measure --once <dir>
"""

import json
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

SAMPLES = 5

# Texts for the prediction timing, short like the evaluation set.
PROBE_TEXTS = (
    "My flight was delayed and nobody helped me.",
    "The staff were helpful.",
    "The flight landed at 6pm.",
)
PREDICTIONS_PER_SAMPLE = 30


def peak_rss_bytes() -> int:
    """Peak resident set size of this process.

    ru_maxrss is bytes on macOS and kilobytes on Linux. Container limits are
    set from the peak rather than the current value, so the peak is what this
    reports; getting the unit wrong would be a 1024x error in a sizing number.
    """
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw if sys.platform == "darwin" else raw * 1024


def measure_once(model_dir: Path) -> dict:
    """Load the model once, then time some predictions, in this process."""
    baseline = peak_rss_bytes()

    # Timed apart because they scale differently and P03-P04 need them apart:
    # importing the frameworks costs the same whatever the weights are, while
    # reading the weights scales with the artifact.
    started = time.perf_counter()
    import torch  # noqa: F401
    import transformers  # noqa: F401

    from feedbackpulse.inference import SentimentClassifier

    import_done = time.perf_counter()
    after_import = peak_rss_bytes()

    classifier = SentimentClassifier.load(model_dir, model_version="measure")
    loaded = time.perf_counter()
    after_load = peak_rss_bytes()

    latencies = []
    for index in range(PREDICTIONS_PER_SAMPLE):
        text = PROBE_TEXTS[index % len(PROBE_TEXTS)]
        start = time.perf_counter()
        classifier.predict(text)
        latencies.append(time.perf_counter() - start)

    return {
        "framework_import_seconds": round(import_done - started, 3),
        "weights_load_seconds": round(loaded - import_done, 3),
        "total_startup_seconds": round(loaded - started, 3),
        "baseline_peak_rss_bytes": baseline,
        "peak_rss_after_import_bytes": after_import,
        "peak_rss_after_load_bytes": after_load,
        "peak_rss_after_predictions_bytes": peak_rss_bytes(),
        "framework_bytes_peak_delta": after_import - baseline,
        "weights_bytes_peak_delta": after_load - after_import,
        "model_bytes_peak_delta": after_load - baseline,
        "predictions": PREDICTIONS_PER_SAMPLE,
        "predict_mean_ms": round(statistics.mean(latencies) * 1000, 2),
        "predict_median_ms": round(statistics.median(latencies) * 1000, 2),
        "predict_max_ms": round(max(latencies) * 1000, 2),
    }


def _summarise(key: str, samples: list[dict]) -> dict:
    values = [sample[key] for sample in samples]
    return {"min": min(values), "max": max(values), "median": statistics.median(values)}


def run(model_dir: Path, samples: int = SAMPLES) -> dict:
    """Spawn one process per sample and summarise the range."""
    collected = []
    for _ in range(samples):
        output = subprocess.run(
            [sys.executable, "-m", "feedbackpulse.measure", "--once", str(model_dir)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        collected.append(json.loads(output))

    return {
        "model_dir": str(model_dir),
        "samples": samples,
        "platform": f"{sys.platform} {sys.version.split()[0]}",
        "per_sample": collected,
        "summary": {
            key: _summarise(key, collected)
            for key in (
                "framework_import_seconds",
                "weights_load_seconds",
                "total_startup_seconds",
                "peak_rss_after_load_bytes",
                "framework_bytes_peak_delta",
                "weights_bytes_peak_delta",
                "model_bytes_peak_delta",
                "predict_median_ms",
                "peak_rss_after_predictions_bytes",
            )
        },
    }


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "--once":
        print(json.dumps(measure_once(Path(sys.argv[2]))))
        return

    artifacts = sorted(Path("artifacts").glob("sentiment-*"))
    if not artifacts:
        print("no packaged artifact found", file=sys.stderr)
        raise SystemExit(1)

    result = run(artifacts[0] / "model")
    mib = 1024**2
    summary = result["summary"]
    print(f"model_dir : {result['model_dir']}")
    print(f"samples   : {result['samples']} fresh processes on {result['platform']}")
    for key in (
        "framework_import_seconds",
        "weights_load_seconds",
        "total_startup_seconds",
        "predict_median_ms",
    ):
        row = summary[key]
        print(
            f"  {key:<26} min={row['min']:<8} median={row['median']:<8} max={row['max']}"
        )
    for key in (
        "framework_bytes_peak_delta",
        "weights_bytes_peak_delta",
        "peak_rss_after_load_bytes",
        "peak_rss_after_predictions_bytes",
    ):
        row = summary[key]
        print(
            f"  {key:<26} min={row['min'] / mib:.0f} MiB  "
            f"median={row['median'] / mib:.0f} MiB  max={row['max'] / mib:.0f} MiB"
        )


if __name__ == "__main__":
    main()

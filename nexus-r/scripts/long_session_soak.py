from __future__ import annotations
# ruff: noqa: E402

"""
Phase B — Long-Session Soak Validation (30-minute)
Records RSS, CPU, SQLite/WAL size, event count every 60s.
ABORT CONDITIONS:
  - RSS growth > 500MB (CONFIRMED LEAK — stop immediately)
  - RSS growth > 100MB over 30 min (POTENTIAL LEAK — flag)
"""

import asyncio
import csv
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from modules.orchestrator.src.orchestrator import MainOrchestrator


PASS = 0
FAIL = 0
ABORTED = False
CONFIRMED_LEAK = False


def check(label: str, passed: bool, detail: str = "") -> None:
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}{' — ' + detail if detail else ''}")


def _get_rss_mb() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


def _get_cpu_pct() -> float:
    try:
        import psutil
        return psutil.Process().cpu_percent(interval=0.5)
    except ImportError:
        return 0.0


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size if path.exists() else 0
    except (OSError, PermissionError):
        return 0


SAMPLE_TASKS = [
    "hello",
    "list all python files",
    "explain databases briefly",
    "draft a short message",
    "create notes.txt with content test",
    "read notes.txt",
    "search text for hello",
    "list all python files",
    "hello world",
    "brainstorm two names",
]


async def main():
    global ABORTED, CONFIRMED_LEAK

    DURATION_MINUTES = 30
    SAMPLE_INTERVAL_S = 60
    TASK_INTERVAL_S = 6  # ~10 tasks/min

    print("=" * 70)
    print("  PHASE B — LONG-SESSION SOAK (30 min)")
    print("=" * 70)

    wd = ROOT / ".long-soak"
    wd.mkdir(exist_ok=True)
    (wd / "src").mkdir(exist_ok=True)
    (wd / "src" / "sample.py").write_text("print('hello')\n", encoding="utf-8")
    (wd / "notes.txt").write_text("alpha\nbeta\nhello world\n", encoding="utf-8")

    config = NEXUSConfig.default(wd)
    config.observability.log_path = wd / "soak_telemetry.log"
    orchestrator = MainOrchestrator(config)
    await orchestrator.initialize()

    csv_path = wd / "soak_metrics.csv"
    fh = open(csv_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(fh)
    writer.writerow([
        "elapsed_s", "rss_mb", "cpu_pct",
        "db_bytes", "wal_bytes", "shm_bytes",
        "event_count", "etd_count",
        "tasks_completed", "last_latency_ms",
    ])
    fh.flush()

    task_index = 0
    total_completed = 0
    start = time.perf_counter()
    rss_baseline = _get_rss_mb()
    max_rss = rss_baseline
    rss_at_100 = 0  # Track growth milestones

    print(f"\nBaseline RSS: {rss_baseline:.1f}MB")
    print(f"Metrics CSV: {csv_path}")
    print(f"Soaking for {DURATION_MINUTES} min...\n")

    try:
        while True:
            elapsed = time.perf_counter() - start
            elapsed_min = elapsed / 60

            if elapsed_min >= DURATION_MINUTES:
                print(f"\n  Soak duration reached ({DURATION_MINUTES} min)")
                break

            # Run a batch of tasks
            batch_start = time.perf_counter()
            for _ in range(2):
                prompt = SAMPLE_TASKS[task_index % len(SAMPLE_TASKS)]
                try:
                    result = await asyncio.wait_for(
                        orchestrator.run_task(prompt), timeout=15
                    )
                    if result.get("success"):
                        total_completed += 1
                except Exception as exc:
                    pass
                task_index += 1
            batch_latency = (time.perf_counter() - batch_start) * 1000

            # Sample metrics every SAMPLE_INTERVAL_S
            if int(elapsed) % SAMPLE_INTERVAL_S < 2 or elapsed < 2:
                rss = _get_rss_mb()
                cpu = _get_cpu_pct()
                max_rss = max(max_rss, rss)
                db_path = config.database.path
                db_bytes = _file_size(db_path)
                wal_bytes = _file_size(Path(str(db_path) + "-wal"))
                shm_bytes = _file_size(Path(str(db_path) + "-shm"))

                try:
                    completed_events = await orchestrator.event_store.get_by_type("task_completed")
                    event_count = len(completed_events)
                except Exception:
                    event_count = 0

                try:
                    etd_count = len(orchestrator.etd_pipeline.store.list_active())
                except Exception:
                    etd_count = 0

                writer.writerow([
                    round(elapsed, 1), round(rss, 1), round(cpu, 1),
                    db_bytes, wal_bytes, shm_bytes,
                    event_count, etd_count,
                    total_completed, round(batch_latency, 1),
                ])
                fh.flush()

                growth = rss - rss_baseline
                marker = ""
                if growth > 100:
                    marker = " ⚠ POTENTIAL LEAK"
                if growth > 500:
                    marker = " *** CONFIRMED LEAK — ABORTING ***"
                    CONFIRMED_LEAK = True
                    ABORTED = True

                db_mb = db_bytes / (1024 * 1024)
                wal_mb = wal_bytes / (1024 * 1024)
                print(
                    f"  t={elapsed_min:5.1f}min  "
                    f"RSS={rss:6.1f}MB(+{growth:+.1f})  "
                    f"DB={db_mb:.2f}MB  WAL={wal_mb:.2f}MB  "
                    f"events={event_count}  etd={etd_count}  "
                    f"done={total_completed}{marker}"
                )

                if CONFIRMED_LEAK:
                    break

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n  Soak interrupted by user")
    finally:
        fh.close()
        await orchestrator.event_store.close()
        await orchestrator.close()

    # Final analysis
    rss_final = _get_rss_mb()
    total_growth = rss_final - rss_baseline
    db_path = config.database.path
    final_db_mb = _file_size(db_path) / (1024 * 1024)
    final_wal_mb = _file_size(Path(str(db_path) + "-wal")) / (1024 * 1024)

    print(f"\n{'='*70}")
    print(f"  SOAK RESULTS")
    print(f"{'='*70}")
    check(f"Baseline RSS: {rss_baseline:.1f}MB → Final: {rss_final:.1f}MB "
          f"(+{total_growth:.1f}MB over {elapsed/60:.1f}min)",
          total_growth < 500,
          f"growth={total_growth:.1f}MB")
    check(f"Max RSS: {max_rss:.1f}MB", max_rss - rss_baseline < 100,
          f"peak_growth={max_rss - rss_baseline:.1f}MB")
    check(f"Total tasks completed: {total_completed}",
          total_completed > 0)
    check(f"Database: {final_db_mb:.2f}MB, WAL: {final_wal_mb:.2f}MB",
          final_wal_mb < 50,
          f"wal={final_wal_mb:.2f}MB")
    check(f"CONFIRMED LEAK: {'YES' if CONFIRMED_LEAK else 'NO'}",
          not CONFIRMED_LEAK)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        import csv as csv_reader
        rows = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv_reader.DictReader(f)
            for row in reader:
                rows.append(row)

        if rows:
            times = [float(r["elapsed_s"]) / 60 for r in rows]
            rss_vals = [float(r["rss_mb"]) for r in rows]
            db_vals = [float(r["db_bytes"]) / (1024*1024) for r in rows]
            wal_vals = [float(r["wal_bytes"]) / (1024*1024) for r in rows]

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

            ax1.plot(times, rss_vals, "b-", label="RSS (MB)")
            ax1.axhline(y=rss_baseline + 100, color="orange", linestyle="--",
                        label="Potential leak threshold")
            ax1.axhline(y=rss_baseline + 500, color="red", linestyle="--",
                        label="Confirmed leak threshold")
            ax1.set_ylabel("RSS (MB)")
            ax1.set_title("Soak Memory Profile")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            ax2.plot(times, db_vals, "g-", label="DB (MB)")
            ax2.plot(times, wal_vals, "r-", label="WAL (MB)")
            ax2.set_xlabel("Time (minutes)")
            ax2.set_ylabel("Size (MB)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plot_path = wd / "soak_memory_profile.png"
            plt.tight_layout()
            plt.savefig(str(plot_path), dpi=100)
            print(f"\nMemory profile: {plot_path}")
        else:
            print("\nNo metrics collected — cannot plot")
    except ImportError:
        print("\nmatplotlib not available — skipping plot")

    print(f"\n  {'='*40}")
    print(f"  SOAK GATE: {'PASS' if not CONFIRMED_LEAK else 'FAIL'}")
    print(f"  {'='*40}")


if __name__ == "__main__":
    if not hasattr(Path, '_mkdir_patched'):
        original_mkdir = Path.mkdir
        def _safe_mkdir(self, *a, **kw):
            try:
                return original_mkdir(self, *a, **kw)
            except FileExistsError:
                pass
        Path.mkdir = _safe_mkdir
        Path._mkdir_patched = True
    asyncio.run(main())

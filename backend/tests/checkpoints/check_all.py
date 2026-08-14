"""
Master Runner: Executes all module checkpoints sequentially.
Displays a clean progress bar and stops on any failing module.
"""
import subprocess
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent

CHECKPOINTS = [
    ("M0: Data Models & Mock Data",  root_dir / "tests" / "checkpoints" / "check_m0_models.py"),
    ("M1: Deduplication Engine",     root_dir / "tests" / "checkpoints" / "check_m1_dedup.py"),
    ("M2: Root-Cause Clustering",   root_dir / "tests" / "checkpoints" / "check_m2_cluster.py"),
    ("M3: Knowledge Base & Tiers",  root_dir / "tests" / "checkpoints" / "check_m3_knowledge.py"),
    ("M4: Domain Specialists",      root_dir / "tests" / "checkpoints" / "check_m4_specialists.py"),
    ("M5: AI Pipeline & Orchestrator", root_dir / "tests" / "checkpoints" / "check_m5_orchestrator.py"),
    ("M6: Sandbox Proof Simulator", root_dir / "tests" / "checkpoints" / "check_m6_simulator.py"),
    ("M7: FastAPI Layer",           root_dir / "tests" / "checkpoints" / "check_m7_api.py"),
]


def main():
    print("\n" + "=" * 65)
    print("  🚀 CODELOOM AUDIT ENGINE — FULL SYSTEM CHECKPOINT RUNNER")
    print("=" * 65)

    passed_count = 0
    total = len(CHECKPOINTS)

    for name, script_path in CHECKPOINTS:
        print(f"\n  ▶ Executing {name}...")
        try:
            # Import module directly to execute inside current runtime
            import importlib.util
            spec = importlib.util.spec_from_file_location("checkpoint_module", script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            passed = module.main()
        except Exception as e:
            print(f"  ❌ Error executing checkpoint {name}: {e}")
            passed = False

        if passed:
            passed_count += 1
        else:
            print(f"\n  🛑 System check stopped at {name}. Fix this module before proceeding.")
            break

    print("\n" + "=" * 65)
    bar_width = 30
    filled = int((passed_count / total) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    pct = round((passed_count / total) * 100, 1)

    print(f"  SYSTEM STATUS: [{bar}] {pct}% ({passed_count}/{total} Modules Verified)")
    print("=" * 65)

    if passed_count == total:
        print("\n  🎉 ALL 8 MODULES VERIFIED & PASSING! The engine is 100% ready for integration.\n")
    else:
        print(f"\n  👉 Progress paused at module index {passed_count}. Resolve above errors.\n")


if __name__ == "__main__":
    main()

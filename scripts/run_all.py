"""Run the whole pipeline in order: python scripts/run_all.py"""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for name in ("run_pipeline.py", "land_based.py", "final_outputs.py", "export_dashboard_data.py"):
    print(f"\n=== {name} ===")
    subprocess.run([sys.executable, str(HERE / name)], check=True)
print("\nAll steps finished.")
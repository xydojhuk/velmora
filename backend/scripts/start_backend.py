from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

marker = Path(os.getenv("VELMORA_INSTALLED_FILE", "/run/velmora/config/installed.json"))
print(f"Velmora backend waiting for installation marker: {marker}", flush=True)
while not marker.is_file():
    time.sleep(2)

print("Installation marker found. Applying database migrations...", flush=True)
subprocess.run(["alembic", "upgrade", "head"], cwd="/app", check=True)
print("Starting Velmora API...", flush=True)
os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])

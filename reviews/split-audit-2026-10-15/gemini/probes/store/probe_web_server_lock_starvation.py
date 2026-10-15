"""
Probe: Verify lock starvation on get_status during pause_sweep.
Finding ID: G-STORE-05

Demonstrates that pause_sweep() holds self.lock while blocking on proc.wait(timeout=6.0),
starving concurrent get_status() calls from web clients.
"""
import copy
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from seed_search.web.server import SweepManager


def test_pause_sweep_lock_starvation(tmp_path):
    manager = SweepManager()
    manager.run_dir = tmp_path
    manager.run_id = "test-run"
    manager.status = "running"
    
    script = (
        "import signal, sys, time\n"
        "signal.signal(signal.SIGINT, signal.SIG_IGN)\n"
        "sys.stdout.write('READY\\n')\n"
        "sys.stdout.flush()\n"
        "time.sleep(2.0)\n"
    )
    proc = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True)
    line = proc.stdout.readline()
    assert line.strip() == "READY"
    manager.process = proc
    
    # Time how long get_status is blocked during pause_sweep
    status_latencies = []
    
    def poller():
        time.sleep(0.1)  # wait for pause_sweep to acquire lock
        t0 = time.time()
        print("[Probe] Client sending GET /api/sweep/status (calling get_status())...")
        st = manager.get_status()
        dt = time.time() - t0
        print(f"[Probe] get_status() unblocked after {dt:.3f}s! Status: {st['status']}")
        status_latencies.append(dt)
        
    poller_thread = threading.Thread(target=poller)
    poller_thread.start()
    
    t_start = time.time()
    print("[Probe] Calling manager.pause_sweep()...")
    res = manager.pause_sweep()
    t_pause = time.time() - t_start
    print(f"[Probe] pause_sweep() returned after {t_pause:.3f}s with: {res}")
    
    poller_thread.join()
    
    assert len(status_latencies) == 1
    latency = status_latencies[0]
    print(f"[Probe] Polling request was blocked for {latency:.3f}s while holding manager.lock.")
    
    if latency > 1.5:
        print("[BUG CONFIRMED] G-STORE-05: Web server get_status was starved for > 1.5s while pause_sweep blocked on subprocess!")
        return True
    return False


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        success = test_pause_sweep_lock_starvation(Path(td))
        if not success:
            sys.exit(1)
        print("Probe completed successfully.")

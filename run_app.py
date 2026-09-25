# run_app.py -- one-command launcher for the Rubik's cube web app.
#
# Starts (and keeps alive) both servers:
#   * Flask web app     -> http://127.0.0.1:5000
#   * Streamlit DAA dash -> http://127.0.0.1:8501
#
# The Streamlit dashboard binds IPv4 loopback only (--server.address
# 127.0.0.1): an IPv6 dual-stack bind dies with WinError 64 when the
# Wi-Fi/hotspot network blips and the page then hangs on "loading".
#
# Every 3 seconds each server is health-checked; a dead one is restarted
# automatically.  Press Ctrl+C to stop.

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

FLASK_CMD = [PY, "viz/app.py"]
STREAMLIT_CMD = [
    PY, "-m", "streamlit", "run", "daa/ui/app.py",
    "--server.headless", "true",
    "--server.port", "8501",
    "--server.address", "127.0.0.1",
]

FLASK_URL = "http://127.0.0.1:5000/"
ST_URL = "http://127.0.0.1:8501/_stcore/health"


def alive(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status < 500
    except Exception:
        return False


def pid_on_port(port: int) -> int | None:
    """PID listening on TCP port (Windows), or None if none/unknown."""
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=5
        ).stdout
    except Exception:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "TCP" and parts[3] == "LISTENING":
            try:
                if parts[1].endswith(f":{port}"):
                    return int(parts[4])
            except ValueError:
                continue
    return None


def kill_pid(pid: int | None) -> None:
    if not pid:
        return
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=5)
    except Exception:
        pass


def free_port(port: int) -> None:
    """Hard-free a port: on Windows the wedged process still holds the socket."""
    kill_pid(pid_on_port(port))


def start(name: str, cmd: list[str]) -> subprocess.Popen:
    # A failed/replaced child stays alive holding the port; kill it first so
    # the replacement can actually bind (Streamlit often wedges on this
    # hotspot and keeps 8501 even though /_stcore/health is dead).
    free_port({"flask": 5000, "streamlit": 8501}.get(name))
    print(f"[run_app] starting {name} ...", flush=True)
    return subprocess.Popen(
        cmd, cwd=str(ROOT),
        stdout=open(ROOT / f".run_app_{name}.log", "ab"),
        stderr=subprocess.STDOUT, close_fds=True,
    )


def main() -> None:
    print("[run_app] Rubik's cube app launcher")
    print(f"[run_app]   web app       -> {FLASK_URL}")
    print(f"[run_app]   DAA dashboard -> http://127.0.0.1:8501/")
    flask = start("flask", FLASK_CMD)
    st = start("streamlit", STREAMLIT_CMD)
    try:
        while True:
            if not alive(FLASK_URL):
                print("[run_app] Flask down -- restarting", flush=True)
                if flask and flask.poll() is None:
                    try:
                        flask.terminate()
                    except Exception:
                        pass
                flask = start("flask", FLASK_CMD)
            if not alive(ST_URL):
                print("[run_app] Streamlit down -- restarting", flush=True)
                if st and st.poll() is None:
                    try:
                        st.terminate()
                    except Exception:
                        pass
                st = start("streamlit", STREAMLIT_CMD)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[run_app] stopping ...")
    finally:
        for p in (flask, st):
            if p.poll() is None:
                p.terminate()


if __name__ == "__main__":
    main()
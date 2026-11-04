#!/usr/bin/env python3
"""Optional local Admin/Tracking previews; reuses the owned synthetic Cloud runtime.
No environment publication or credentials are created by this helper.
"""
import argparse, os, pathlib, signal, time
import dev

PORTALS = [("admin", "NexoRuta.Admin", 5103), ("tracking", "NexoRuta.Tracking", 5104)]

def stop():
    for name, project, port in PORTALS:
        marker = dev.STATE / (name + ".pid")
        if not marker.exists(): continue
        pid = int(marker.read_text())
        try:
            identity = (dev.STATE / (name + ".identity")).read_text()
            if identity not in pathlib.Path(f"/proc/{pid}/cmdline").read_text():
                raise RuntimeError("Refusing to stop an unrelated process")
            os.killpg(pid, signal.SIGTERM)
        except (ProcessLookupError, FileNotFoundError): pass
        marker.unlink()
    print("Owned optional portal previews stopped")

def start():
    state = dev.load()
    for name, project, port in PORTALS:
        marker = dev.STATE / (name + ".pid")
        if marker.exists():
            raise RuntimeError("Stop optional portal previews before rebuilding")
        dev.run(["dotnet", "build", dev.ROOT / "frontend/src" / project,
                 "--artifacts-path", dev.STATE / "artifacts", "--nologo"])
        dev.launch(state, name, project, port)
        for _ in range(60):
            try:
                dev.LOCAL_HTTP.open(f"http://127.0.0.1:{port}/", timeout=2)
                break
            except Exception: time.sleep(.25)
        else: raise RuntimeError(f"Portal {port} failed readiness; inspect its private log")
    print("Local portal previews: Admin5103 Tracking5104")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "stop"])
    globals()[parser.parse_args().command]()

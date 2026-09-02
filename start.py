import os
import sys
import uvicorn

if __name__ == "__main__":
    port_str = os.environ.get("PORT", "10000")
    try:
        port = int(port_str)
    except ValueError:
        port = 10000

    print(f"[SCOUTIFY_BOOT] Starting FastAPI Backend on 0.0.0.0:{port}...", flush=True)
    try:
        uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as exc:
        print(f"[SCOUTIFY_CRITICAL] Server failed to start: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

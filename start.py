import os
import sys
import traceback
import uvicorn

if __name__ == "__main__":
    port_str = os.environ.get("PORT", "10000")
    try:
        port = int(port_str)
    except ValueError:
        port = 10000

    print(f"[SCOUTIFY_BOOT] Starting Uvicorn on 0.0.0.0:{port}...", flush=True)
    try:
        uvicorn.run(
            "backend.app.main:app",
            host="0.0.0.0",
            port=port,
            log_level="info",
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
    except Exception as exc:
        print(f"[SCOUTIFY_BOOT_ERROR] Failed during uvicorn.run: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

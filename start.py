import os
import sys
import traceback

if __name__ == "__main__":
    port_str = os.environ.get("PORT", "10000")
    try:
        port = int(port_str)
    except ValueError:
        port = 10000

    print(f"[SCOUTIFY_BOOT] Verifying backend application imports...", flush=True)
    try:
        from backend.app.main import app
        print(f"[SCOUTIFY_BOOT] Successfully imported Scoutify FastAPI app.", flush=True)
    except Exception as exc:
        print(f"[SCOUTIFY_IMPORT_ERROR] Critical failure importing FastAPI app: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    print(f"[SCOUTIFY_BOOT] Starting Uvicorn server on 0.0.0.0:{port}...", flush=True)
    try:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as exc:
        print(f"[SCOUTIFY_BOOT_ERROR] Failed during uvicorn.run: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

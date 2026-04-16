import os
import os
import subprocess


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    if truthy(os.getenv("RUN_MIGRATIONS", "true")):
        subprocess.check_call(["alembic", "upgrade", "head"])

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = os.getenv("UVICORN_PORT", "8000")
    args = ["uvicorn", "app.main:app", "--host", host, "--port", port]
    if truthy(os.getenv("UVICORN_RELOAD", "false")):
        args.append("--reload")
    os.execvp(args[0], args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

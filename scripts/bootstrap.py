import os
import shutil
import subprocess
import time


def run(command: list[str]) -> int:
    print("+", " ".join(command))
    return subprocess.call(command)


def main() -> int:
    required = [
        "OPENAI_API_KEY",
        "DATABASE_URL",
        "SIGNAL_API_BASE_URL",
        "SIGNAL_BOT_NUMBER",
        "SIGNAL_WEBHOOK_SECRET",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if not (os.getenv("ADMIN_API_TOKEN") or os.getenv("ADMIN_API_TOKENS")):
        missing.append("ADMIN_API_TOKEN or ADMIN_API_TOKENS")
    if shutil.which("docker") is None:
        print("Docker is not installed or not in PATH.")
        return 1
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        return 1
    print("Starting Docker Compose dependencies...")
    if run(["docker", "compose", "up", "-d", "postgres", "signal-cli-rest-api"]) != 0:
        return 1
    print("Waiting for Postgres to become healthy...")
    time.sleep(10)
    print("Running Alembic migrations in the container...")
    if run(["docker", "compose", "run", "--rm", "app", "alembic", "upgrade", "head"]) != 0:
        return 1
    print("Bootstrap complete.")
    print("Next steps:")
    print("1. Register the bot's primary Signal account via signal-cli-rest-api using SIGNAL_BOT_NUMBER.")
    print("2. Verify the registration code through the REST API.")
    print("3. Start the app with `docker compose up app` or `make dev`.")
    print("4. Send a group message and confirm it appears in admin group listing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

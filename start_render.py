import os
import signal
import subprocess
import sys
import time


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    port = os.getenv("PORT", "8000")
    mcp_port = os.getenv("MCP_PORT", "8001")

    env = os.environ.copy()
    env.setdefault("BACKEND_API_BASE_URL", f"http://127.0.0.1:{port}")
    env.setdefault("BUDGET_API_BASE_URL", f"http://127.0.0.1:{port}")
    env.setdefault("MCP_HOST", "127.0.0.1")
    env["MCP_PORT"] = mcp_port
    env.setdefault("MCP_SERVER_URL", f"http://127.0.0.1:{mcp_port}/mcp")

    processes = [
        (
            "backend",
            subprocess.Popen(
                ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", port],
                env=env,
            ),
            True,
        ),
        ("mcp_server", subprocess.Popen(["python", "-m", "mcp_server.server"], env=env), True),
    ]

    if env_bool("TELEGRAM_BOT_ENABLED", True):
        processes.append(
            (
                "telegram_bot",
                subprocess.Popen(["python", "-m", "telegram_bot.src.bot.main"], env=env),
                False,
            )
        )

    stopping = False

    def stop(_signum=None, _frame=None):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for _name, process, _critical in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        while True:
            for name, process, critical in processes:
                return_code = process.poll()
                if return_code is not None:
                    if not critical:
                        print(
                            f"{name} exited with status {return_code}; backend and MCP will keep running.",
                            flush=True,
                        )
                        processes.remove((name, process, critical))
                        continue
                    stop()
                    for _child_name, child, _child_critical in processes:
                        if child is not process:
                            try:
                                child.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                child.kill()
                    return return_code
            time.sleep(1)
    finally:
        stop()


if __name__ == "__main__":
    sys.exit(main())

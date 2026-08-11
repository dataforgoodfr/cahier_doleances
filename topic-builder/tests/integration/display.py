"""
Integration test for the `topicbuilder display` subcommand.

Run with:
    python -m tests.integration.display
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "topics_config.json"
STARTUP_TIMEOUT_SECONDS = 60


def _find_free_port() -> int:
    """
    Bind an ephemeral socket to find a free local port to run the Dash server on.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_serving(url: str, timeout_seconds: float) -> httpx.Response:
    """
    Poll the given URL until it responds or the timeout elapses, returning the last response.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            return httpx.get(url, timeout=2)
        except httpx.TransportError:
            time.sleep(0.5)
    raise TimeoutError(f"Server at {url} did not respond within {timeout_seconds}s")


def run() -> None:
    """
    Launch the display server as a subprocess, poll it until ready, and assert it serves a 200 page.
    """
    port = _find_free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "topicbuilder",
            "display",
            "--taxonomy-path",
            str(TAXONOMY_PATH),
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        response = _wait_until_serving(f"http://127.0.0.1:{port}/", STARTUP_TIMEOUT_SECONDS)
        assert process.poll() is None, f"Server exited early:\n{process.stderr.read()}"
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
        assert "Knowledge Graph Viewer" in response.text, "Response missing expected page title"

        print(f"OK — server on port {port} responded with status {response.status_code}.")

    finally:
        process.terminate()
        process.wait(timeout=10)

    return None


if __name__ == "__main__":
    run()

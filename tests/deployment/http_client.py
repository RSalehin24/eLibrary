import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4


@dataclass(frozen=True)
class Response:
    status: int
    headers: str
    body: bytes

    def json(self):
        return json.loads(self.body)


class LocalHTTPSClient:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.cookie = self.directory / f"cookies-{uuid4().hex}.txt"
        self.headers = {}

    def wait_until_ready(self):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if self.request("/api/v1/health/ready/").status == 200:
                return
            time.sleep(1)
        raise AssertionError("The isolated HTTPS proxy did not become ready.")

    def request(self, path, values=None, *, method=None):
        if not path.startswith("/") or urlsplit(path).netloc:
            raise ValueError("Only relative local test paths are accepted.")
        with tempfile.TemporaryDirectory(dir=self.directory) as directory:
            command = self.command(path, Path(directory))
            if method:
                command.extend(["--request", method])
            if values is not None:
                command.extend(
                    ["--data-binary", "@-", "-H", "Content-Type: application/json"]
                )
            result = subprocess.run(
                command,
                input=json.dumps(values).encode() if values is not None else None,
                capture_output=True,
                check=False,
            )
            if result.returncode in {7, 28, 35, 52, 56}:
                return Response(0, "", b"")
            if result.returncode:
                raise RuntimeError(
                    f"Local HTTPS probe failed: curl error {result.returncode}."
                )
            return Response(
                int(result.stdout),
                (Path(directory) / "headers").read_text(),
                (Path(directory) / "body").read_bytes(),
            )

    def command(self, path, directory):
        command = [
            "curl",
            "--silent",
            "--show-error",
            "--noproxy",
            "*",
            "--max-time",
            "15",
            "--cacert",
            str(self.directory / "tls/fullchain.pem"),
            "--resolve",
            "library.example.test:18443:127.0.0.1",
            "--cookie",
            str(self.cookie),
            "--cookie-jar",
            str(self.cookie),
            "--dump-header",
            str(directory / "headers"),
            "--output",
            str(directory / "body"),
            "--write-out",
            "%{http_code}",
        ]
        for name, value in self.headers.items():
            command.extend(["-H", f"{name}: {value}"])
        return command + ["https://library.example.test:18443" + path]

    def authenticate(self, account):
        session = account["session"]
        descriptor = os.open(self.cookie, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(
                "# Netscape HTTP Cookie File\n"
                f"library.example.test\tFALSE\t/\tTRUE\t0\t{session['name']}\t{session['value']}\n"
            )
        response = self.request("/api/v1/auth/session/")
        assert response.status == 200 and response.json()["authenticated"], (
            "Session verification failed."
        )
        self.headers["X-CSRFToken"] = response.json()["csrf_token"]
        self.headers["Origin"] = "https://library.example.test:18443"

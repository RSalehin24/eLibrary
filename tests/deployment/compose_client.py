import json
import os
import subprocess
from pathlib import Path


class IsolatedCompose:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.command = [
            "docker",
            "compose",
            "--env-file",
            str(self.directory / "platform.env"),
            "-f",
            str(Path(__file__).resolve().parents[2] / "deploy/compose/platform.yml"),
        ]
        configuration = json.loads(self.call("config", "--format", "json"))
        api = configuration["services"]["api"]["environment"]
        if (
            not configuration["name"].startswith("elibrary-platform-test-")
            or api["FRONTEND_BASE_URL"] != "https://library.example.test:18443"
            or api["APP_ENV"] != "production"
        ):
            raise RuntimeError("This command requires the isolated local test project.")
        self.project = configuration["name"]

    def call(self, *arguments, data=None):
        result = subprocess.run(
            self.command + list(arguments),
            input=data,
            capture_output=True,
            check=False,
            timeout=180,
        )
        if result.returncode:
            raise RuntimeError(f"Isolated Compose command failed: {arguments[:2]}.")
        return result.stdout

    def install_script(self, path):
        target = "/tmp/" + path.name
        self.call(
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "import sys; from pathlib import Path; Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())",
            target,
            data=path.read_bytes(),
        )

    def prepare_scripts(self):
        root = Path(__file__).resolve().parents[2]
        for path in (
            root / "tests/web/seed_preview.py",
            root / "tests/web/seed_reader.py",
            root / "tests/deployment/seed_platform.py",
            root / "tests/deployment/job_probe.py",
            root / "tests/deployment/interruption_fixture.py",
        ):
            self.install_script(path)

    def probe(self, action, identifier=None):
        command = [
            "exec",
            "-T",
            "-e",
            "PYTHONPATH=/app:/tmp",
            "-e",
            "ALLOW_DEPLOYMENT_FIXTURES=isolated-local-verification",
            "api",
            "python",
            "/tmp/job_probe.py",
            action,
        ]
        if identifier:
            command.extend(["--identifier", str(identifier)])
        fixture = json.loads((self.directory / "fixture.json").read_text())
        return json.loads(self.call(*command, data=json.dumps(fixture).encode()))

    def seed(self):
        self.prepare_scripts()
        self.call(
            "exec",
            "-T",
            "-e",
            "PYTHONPATH=/app:/tmp",
            "-e",
            "ALLOW_DEPLOYMENT_FIXTURES=isolated-local-verification",
            "-e",
            "DEPLOYMENT_FIXTURE_PATH=/tmp/deployment-fixture.json",
            "api",
            "python",
            "/tmp/seed_platform.py",
        )
        values = self.call("exec", "-T", "api", "cat", "/tmp/deployment-fixture.json")
        descriptor = os.open(
            self.directory / "fixture.json",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(values)


if __name__ == "__main__":
    IsolatedCompose(os.environ["DEPLOYMENT_TEST_DIRECTORY"]).seed()
    print("Isolated deployment fixture created privately.")

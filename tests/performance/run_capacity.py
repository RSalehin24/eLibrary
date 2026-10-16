"""Run the pinned k6 harness only against the isolated local HTTPS project."""

import argparse
import ipaddress
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from tests.deployment.compose_client import IsolatedCompose
from tests.deployment.http_client import LocalHTTPSClient

K6_IMAGE = "grafana/k6:2.3.0@sha256:9c2dee7f8ed74d317e4027c06a10f169b625638189de8d4555d0b3486a5aeb34"
ROOT = Path(__file__).resolve().parents[2]


def docker_output(*arguments):
    result = subprocess.run(
        ["docker", *arguments], capture_output=True, check=False, timeout=30
    )
    if result.returncode:
        raise RuntimeError(f"Docker capacity command failed: {arguments[:2]}.")
    return result.stdout.decode().strip()


def proxy_address(stack, configuration):
    identifier = stack.call("ps", "-q", "proxy").decode().strip()
    networks = json.loads(
        docker_output(
            "inspect", "--format", "{{json .NetworkSettings.Networks}}", identifier
        )
    )
    network = configuration["networks"]["outbound"]["name"]
    address = str(ipaddress.IPv4Address(networks[network]["IPAddress"]))
    return network, address


def write_json(path, values):
    with path.open("x") as stream:
        json.dump(values, stream, indent=2)
        stream.write("\n")


def bind_mount(source, target):
    return ["--mount", f"type=bind,src={source},dst={target},readonly"]


def container_command(directory, artifacts, network):
    command = [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "--name",
        f"elibrary-capacity-{artifacts.name}",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--network",
        network,
        "--cpus",
        "1",
        "--memory",
        "256m",
        "--tmpfs",
        "/tmp",
        "--env",
        "SSL_CERT_FILE=/private/fullchain.pem",
        "--env",
        "K6_NO_USAGE_REPORT=true",
        "--env",
        "K6_AUTO_EXTENSION_RESOLUTION=false",
    ]
    for source, target in (
        (directory / "fixture.json", "/private/fixture.json"),
        (directory / "tls/fullchain.pem", "/private/fullchain.pem"),
        (artifacts / "config.json", "/private/config.json"),
        (ROOT / "tests/performance/capacity.mjs", "/capacity.mjs"),
    ):
        command.extend(bind_mount(source, target))
    command.extend(["--mount", f"type=bind,src={artifacts},dst=/artifacts"])
    return command + [
        K6_IMAGE,
        "run",
        "--quiet",
        "--log-output",
        "none",
        "--include-system-env-vars=false",
        "--config",
        "/private/config.json",
    ]


def run_environment(arguments, configuration, hardware):
    api = configuration["services"]["api"]["environment"]
    return {
        "CAPACITY_FIXTURE_PATH": "/private/fixture.json",
        "CAPACITY_REPORT": "/artifacts/summary.json",
        "CAPACITY_VUS": str(arguments.users),
        "CAPACITY_HOLD": f"{arguments.hold_seconds}s",
        "APPLICATION_HARDWARE": f"shared Docker VM: {hardware['cpu_count']} CPU, {hardware['memory_bytes']} bytes RAM; {hardware['architecture']}; API {api['API_WORKERS']} workers x {api['API_THREADS']} threads; one API/frontend replica",
        "LOAD_GENERATOR_HARDWARE": "same Colima VM; container limited to 1 CPU and 256 MiB; direct private Docker network",
    }


def record_utilization(stack, directory):
    identifiers = stack.call("ps", "-q").decode().split()
    samples = docker_output(
        "stats", "--no-stream", "--format", "{{json .}}", *identifiers
    )
    with (directory / "utilization.jsonl").open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "time": time.time(),
                    "containers": [json.loads(line) for line in samples.splitlines()],
                }
            )
            + "\n"
        )


def execute(invocation, stack, artifacts):
    deadline = time.monotonic() + invocation["timeout"]
    with (artifacts / "runtime.log").open("x") as log:
        process = subprocess.Popen(
            invocation["command"], stdout=log, stderr=subprocess.STDOUT
        )
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "The isolated capacity run exceeded its deadline."
                    )
                record_utilization(stack, artifacts)
                time.sleep(3)
            return process.returncode
        finally:
            if process.poll() is None:
                docker_output("stop", "--time", "5", invocation["container_name"])
                process.wait(timeout=15)


def image_provenance(configuration):
    images = {service["image"] for service in configuration["services"].values()}
    return {
        image: docker_output("image", "inspect", "--format", "{{.Id}}", image)
        for image in sorted(images | {K6_IMAGE})
    }


def docker_hardware():
    template = '{"cpu_count":{{.NCPU}},"memory_bytes":{{.MemTotal}},"architecture":{{json .Architecture}},"kernel":{{json .KernelVersion}}}'
    return json.loads(docker_output("info", "--format", template))


def catalog_counts(stack):
    script = "import os, django, json; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); from apps.catalog.models import Book; print(json.dumps({'total': Book.objects.count(), 'published_approved': Book.objects.filter(state='published', review_state='approved').count()}))"
    return json.loads(stack.call("exec", "-T", "api", "python", "-c", script))


def validate_summary(path):
    try:
        metrics = json.loads(path.read_text())["metrics"]
        checks = metrics.get("checks_succeeded", metrics.get("checks"))["values"]
        if (
            checks["rate"] != 1
            or not 0 <= metrics["http_req_failed"]["values"]["rate"] < 0.01
        ):
            raise ValueError("The workload contains failed requests.")
        if any(
            not metrics[name]["values"]["count"] > 0
            for name in ("iterations", "public_latency_ms", "reading_latency_ms")
        ):
            raise ValueError("The workload has missing samples.")
    except (OSError, ValueError, KeyError, TypeError):
        raise RuntimeError(
            "Capacity summary does not show a completed successful workload."
        ) from None


def run(arguments):
    stack = IsolatedCompose(arguments.directory)
    configuration = json.loads(stack.call("config", "--format", "json"))
    directory = Path(arguments.directory).resolve()
    LocalHTTPSClient(directory).wait_until_ready()
    artifacts = Path(
        tempfile.mkdtemp(prefix="k6-", dir=ROOT / "test-artifacts/performance")
    )
    network, address = proxy_address(stack, configuration)
    write_json(
        artifacts / "config.json",
        {"hosts": {"library.example.test:18443": f"{address}:443"}},
    )
    command = container_command(directory, artifacts, network)
    hardware = docker_hardware()
    corpus = catalog_counts(stack)
    for name, value in run_environment(arguments, configuration, hardware).items():
        command.extend(["--env", f"{name}={value}"])
    command.append("/capacity.mjs")
    invocation = {
        "command": command,
        "timeout": arguments.hold_seconds + 120,
        "container_name": f"elibrary-capacity-{artifacts.name}",
    }
    result = execute(invocation, stack, artifacts)
    if result == 0:
        validate_summary(artifacts / "summary.json")
    write_json(
        artifacts / "provenance.json",
        {
            "exit_code": result,
            "images": image_provenance(configuration),
            "scope": "shared-VM functional load simulation",
            "docker_hardware": hardware,
            "catalog_counts": corpus,
        },
    )
    print(
        f"Isolated capacity exit={result}; private artifacts: {artifacts.relative_to(ROOT)}"
    )
    return result


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--users", type=int, default=5)
    parser.add_argument("--hold-seconds", type=int, default=20)
    arguments = parser.parse_args()
    if not 1 <= arguments.users <= 1000 or not 1 <= arguments.hold_seconds <= 3600:
        parser.error("Use 1–1000 users and 1–3600 hold seconds.")
    (ROOT / "test-artifacts/performance").mkdir(parents=True, exist_ok=True)
    return run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())

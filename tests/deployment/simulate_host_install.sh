#!/usr/bin/env bash
set -euo pipefail

if [[ "${ELIBRARY_INSTALL_SIMULATION:-}" != "isolated-container" || ! -f /.dockerenv || -S /var/run/docker.sock ]]; then
  echo "Host installation simulation requires an isolated Docker container without the host socket." >&2
  exit 1
fi
if command -v docker >/dev/null 2>&1; then
  echo "The simulator requires a container without Docker already installed." >&2
  exit 1
fi

mkdir -p /tmp/install-simulator-bin
cat >/tmp/install-simulator-bin/systemctl <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  "enable docker"|"restart docker") printf '%s\n' "$*" >>/artifacts/service-simulation.log ;;
  *) echo "Unexpected systemctl operation in the simulator." >&2; exit 1 ;;
esac
EOF
chmod 0755 /tmp/install-simulator-bin/systemctl
export PATH="/tmp/install-simulator-bin:${PATH}"
bash /scripts/install-docker.sh > /artifacts/install.log 2>&1

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

packages = subprocess.check_output([
    "dpkg-query", "-W", "-f=${Package} ${Version}\n", "docker-ce", "docker-ce-cli",
    "containerd.io", "docker-buildx-plugin", "docker-compose-plugin",
], text=True)
values = {
    "os_release": Path("/etc/os-release").read_text(),
    "docker": subprocess.check_output(["docker", "--version"], text=True).strip(),
    "compose": subprocess.check_output(["docker", "compose", "version"], text=True).strip(),
    "packages": packages.splitlines(),
    "repository": Path("/etc/apt/sources.list.d/docker.list").read_text().strip(),
    "service_operations": Path("/artifacts/service-simulation.log").read_text().splitlines(),
    "scope": "actual container package installation; systemd enable/restart simulated; no Docker daemon or host socket",
}
assert values["service_operations"] == ["enable docker", "restart docker"]
with Path("/artifacts/result.json").open("x") as stream:
    json.dump(values, stream, indent=2)
    stream.write("\n")
print(values["docker"] + "; " + values["compose"] + "; simulator passed")
PY

"""Run each browser specification against freshly seeded, private test records."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SPECIFICATIONS = ROOT / "tests/web/e2e"


def selected_specifications(names):
    paths = [SPECIFICATIONS / name for name in names] if names else sorted(SPECIFICATIONS.glob("*.spec.mjs"))
    for path in paths:
        if path.resolve().parent != SPECIFICATIONS or not path.name.endswith(".spec.mjs") or not path.is_file():
            raise ValueError("Choose existing browser specification filenames.")
    return paths


def private_log(path):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(descriptor, "w")


def run_specification(specification, options):
    artifact = options.artifacts / specification.stem
    artifact.mkdir(mode=0o700)
    environment = {**os.environ, "FOUNDATION_FIXTURE_PATH": str(artifact / "fixture.json")}
    with private_log(artifact / "seed.log") as log:
        subprocess.run([sys.executable, str(ROOT / "tests/web/seed_preview.py")], cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    command = ["node", str(ROOT / "app/web/node_modules/playwright/cli.js"), "test", "--config", str(ROOT / "tests/web/playwright.config.mjs"), specification.name, f"--project={options.project}", f"--output={artifact / 'browser'}"]
    started = monotonic()
    with private_log(artifact / "browser.log") as log:
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, check=False)
    return {"specification": specification.name, "passed": result.returncode == 0, "seconds": round(monotonic() - started, 2), "log": str(artifact / "browser.log")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=["chromium", "webkit", "android", "ios"], required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("specifications", nargs="*")
    options = parser.parse_args()
    try:
        specifications = selected_specifications(options.specifications)
    except ValueError as error:
        parser.error(str(error))
    options.artifacts = (options.artifacts or ROOT / "test-artifacts/foundation" / f"isolated-{options.project}-{uuid4().hex}").resolve()
    options.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    results = []
    for specification in specifications:
        result = run_specification(specification, options)
        results.append(result)
        print(f"{'PASS' if result['passed'] else 'FAIL'} {specification.name}", flush=True)
        with (options.artifacts / "summary.json").open("w") as summary:
            json.dump({"project": options.project, "results": results}, summary, indent=2)
    print(f"Evidence: {options.artifacts}", flush=True)
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

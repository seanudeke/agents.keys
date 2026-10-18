"""Run harmless broker checks inside an explicitly pinned, offline Docker image.

This is a component check, not a prompt-injection evaluation. No agent provider,
GitHub token, source checkout, host credentials or mined workflow is mounted.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def command(image: str, mount: Path) -> list[str]:
    if not re.fullmatch(r"[A-Za-z0-9./:_-]+@sha256:[0-9a-f]{64}", image):
        raise ValueError("supply a locally available Python image pinned by SHA-256 digest")
    code = (
        "import json,os,socket;from broker import boundary_checks;"
        "r=boundary_checks();r['container_uid']=os.getuid();"
        "r['effective_capabilities']=[x.strip() for x in open('/proc/self/status') if x.startswith('CapEff:')];"
        "print(json.dumps(r,sort_keys=True))"
    )
    return ["docker", "run", "--rm", "--pull=never", "--network=none", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=64",
            "--memory=256m", "--cpus=1", "--user=65534:65534",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
            "--mount", f"type=bind,source={mount.resolve()},target=/study,readonly",
            "--workdir=/study", "--env=PYTHONPATH=/study", image, "python", "-c", code]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", required=True)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if not shutil.which("docker"):
        p.error("Docker is required; no container checks were run")
    with tempfile.TemporaryDirectory(prefix="awkeys-boundary-") as directory:
        root = Path(directory)
        root.chmod(0o755)
        broker = Path(__file__).resolve().parents[1] / "src/awkeys/broker.py"
        target = root / "broker.py"
        shutil.copyfile(broker, target)
        target.chmod(0o644)
        result = subprocess.run(command(args.image, root), capture_output=True, text=True,
                                timeout=60, check=True)
    data = json.loads(result.stdout)
    data["record_kind"] = "container_boundary_fixture_check"
    data["container_image"] = args.image
    data["empirical_agent_evaluation"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if all(x["check_passed"] for x in data["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

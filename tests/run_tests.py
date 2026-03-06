#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env={**os.environ, **(env or {})},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def fail(message: str, *, output: str | None = None, code: int = 1) -> None:
    print(f"FAIL: {message}")
    if output:
        print(output.rstrip())
    raise SystemExit(code)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {path}", output=str(exc))
    return {}


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        fail(f"Missing {description}: {path}")


def demo_mode() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    ansible_report = ARTIFACTS_DIR / "ansible_guardrails.json"
    guardrails = run([sys.executable, "tools/ansible_guardrails.py", "--format", "json", "--out", str(ansible_report)])
    if guardrails.returncode != 0:
        fail("Ansible guardrails failed (demo mode must be offline).", output=guardrails.stdout)

    report = load_json(ansible_report)
    if report.get("summary", {}).get("errors", 0) != 0:
        fail("Ansible guardrails reported errors.", output=json.dumps(report.get("findings", []), indent=2))

    demo = run([sys.executable, "pipelines/pipeline_demo.py"])
    if demo.returncode != 0:
        fail("Demo pipeline failed.", output=demo.stdout)

    out_path = REPO_ROOT / "data" / "processed" / "events_jsonl" / "events.jsonl"
    require_file(out_path, "demo pipeline output")
    if out_path.stat().st_size == 0:
        fail("Demo pipeline output is empty.", output=str(out_path))

    require_file(REPO_ROOT / "NOTICE.md", "NOTICE.md")
    require_file(REPO_ROOT / "COMMERCIAL_LICENSE.md", "COMMERCIAL_LICENSE.md")
    require_file(REPO_ROOT / "GOVERNANCE.md", "GOVERNANCE.md")

    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8", errors="replace")
    if "it.freddy.alvarez@gmail.com" not in license_text:
        fail("LICENSE must include the commercial licensing contact email.")

    print("OK: demo-mode tests passed (offline).")


def production_mode() -> None:
    if os.environ.get("PRODUCTION_TESTS_CONFIRM") != "1":
        fail(
            "Production-mode tests require an explicit opt-in.",
            output=(
                "Set `PRODUCTION_TESTS_CONFIRM=1` and rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    missing_imports: list[str] = []
    for mod in ["pandas", "pyarrow", "pandera", "pytest"]:
        try:
            __import__(mod)
        except Exception:
            missing_imports.append(mod)

    if missing_imports:
        fail(
            "Missing Python dependencies for production-mode pipeline/tests.",
            output=(
                "Create a venv and install requirements, then rerun:\n"
                "  make setup\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n\n"
                f"Missing imports: {', '.join(missing_imports)}\n"
            ),
            code=2,
        )

    ran_external_integration = False

    pipeline = run([sys.executable, "pipelines/pipeline.py"])
    if pipeline.returncode != 0:
        fail("Production pipeline failed.", output=pipeline.stdout)
    ran_external_integration = True

    pytest_run = run([sys.executable, "-m", "pytest", "-q"])
    if pytest_run.returncode != 0:
        fail("pytest failed.", output=pytest_run.stdout)

    if os.environ.get("ANSIBLE_VALIDATE") == "1":
        if shutil.which("ansible-playbook") is None:
            fail(
                "ANSIBLE_VALIDATE=1 requires ansible-playbook.",
                output="Install Ansible and rerun production mode, or unset ANSIBLE_VALIDATE.",
                code=2,
            )
        ran_external_integration = True
        syntax = run(["ansible-playbook", "--syntax-check", "ansible/playbooks/harden_linux.yml"])
        if syntax.returncode != 0:
            fail("ansible-playbook --syntax-check failed.", output=syntax.stdout)

    if not ran_external_integration:
        fail("No external integration checks were executed in production mode.", code=2)

    print("OK: production-mode tests passed (integrations executed).")


def main() -> None:
    mode = os.environ.get("TEST_MODE", "demo").strip().lower()
    if mode not in {"demo", "production"}:
        fail("Invalid TEST_MODE. Expected 'demo' or 'production'.", code=2)

    if mode == "demo":
        demo_mode()
        return

    production_mode()


if __name__ == "__main__":
    main()


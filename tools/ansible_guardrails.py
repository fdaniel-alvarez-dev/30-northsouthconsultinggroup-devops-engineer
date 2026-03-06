#!/usr/bin/env python3
import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Finding:
    severity: str  # ERROR | WARN | INFO
    rule_id: str
    message: str
    path: str | None = None


def add(findings: list[Finding], severity: str, rule_id: str, message: str, path: Path | None = None) -> None:
    findings.append(
        Finding(
            severity=severity,
            rule_id=rule_id,
            message=message,
            path=str(path.relative_to(REPO_ROOT)) if path else None,
        )
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def summarize(findings: list[Finding]) -> dict:
    return {
        "errors": sum(1 for f in findings if f.severity == "ERROR"),
        "warnings": sum(1 for f in findings if f.severity == "WARN"),
        "info": sum(1 for f in findings if f.severity == "INFO"),
    }


def check_playbooks(findings: list[Finding]) -> None:
    pb_dir = REPO_ROOT / "ansible" / "playbooks"
    if not pb_dir.exists():
        add(findings, "ERROR", "ansible.playbooks_missing", "ansible/playbooks is missing.", pb_dir)
        return

    playbooks = sorted(pb_dir.glob("*.yml")) + sorted(pb_dir.glob("*.yaml"))
    if not playbooks:
        add(findings, "ERROR", "ansible.playbooks_empty", "No playbooks found under ansible/playbooks.", pb_dir)
        return

    for pb in playbooks:
        text = read_text(pb)
        if not re.search(r"(?m)^\s*hosts:\s*\S+", text):
            add(findings, "ERROR", "ansible.hosts", "Playbook should include a hosts declaration.", pb)
        if not re.search(r"(?m)^\s*become:\s*true\s*$", text):
            add(findings, "WARN", "ansible.become", "Playbook should explicitly set become: true (when hardening OS settings).", pb)
        if "ignore_errors: true" in text:
            add(findings, "WARN", "ansible.ignore_errors", "Avoid ignore_errors: true; handle failures explicitly.", pb)
        if re.search(r"(?m)^\s*-\s+shell:\s*", text):
            add(findings, "WARN", "ansible.shell", "Prefer idempotent modules over shell where possible.", pb)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Ansible guardrails for playbook hygiene.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--out", default="", help="Write output to a file (optional).")
    args = parser.parse_args()

    findings: list[Finding] = []
    check_playbooks(findings)

    report = {"summary": summarize(findings), "findings": [asdict(f) for f in findings]}
    if args.format == "json":
        output = json.dumps(report, indent=2, sort_keys=True)
    else:
        lines = []
        for f in findings:
            where = f" ({f.path})" if f.path else ""
            lines.append(f"{f.severity} {f.rule_id}{where}: {f.message}")
        lines.append("")
        lines.append(f"Summary: {report['summary']}")
        output = "\n".join(lines)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

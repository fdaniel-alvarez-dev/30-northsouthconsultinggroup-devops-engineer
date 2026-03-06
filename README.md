# 30-aws-reliability-security-ansible

A portfolio-grade repository that demonstrates **automation patterns** for secure, repeatable delivery:
an offline-safe demo pipeline, Ansible hardening examples, and CI-friendly guardrails.

## The top pains this repo addresses
1) Replacing manual, risky changes with automated delivery through reviewable automation and guardrails.
2) Shipping fast without compromising security by keeping “secure defaults” cheap to apply and easy to validate.
3) Making validation explicit with deterministic test modes and evidence artifacts.

## Quick demo (local)
```bash
make demo-offline
make test
```

What you get:
- demo-mode pipeline output without third-party dependencies (`pipelines/pipeline_demo.py`)
- offline Ansible playbook hygiene checks (`tools/ansible_guardrails.py`)
- explicit `TEST_MODE=demo|production` tests with production opt-in

## Tests (two explicit modes)

- `TEST_MODE=demo` (default): offline-only checks (no pip installs, no cloud, no credentials)
- `TEST_MODE=production`: real integrations when configured (requires explicit opt-in)

Run demo mode:

```bash
make test-demo
```

Run production mode:

```bash
make test-production
```

Production mode expectations:
- install Python deps with `make setup` (then rerun production mode)
- optionally validate Ansible syntax by setting `ANSIBLE_VALIDATE=1` (requires `ansible-playbook`)

## Ansible example

The folder `ansible/playbooks/` includes a minimal hardening baseline intended as a starting point:
- SSH hardening via idempotent `lineinfile`
- safe handler-based reloads
- clear guardrails in CI (demo mode does not execute changes)

## Sponsorship and contact

Sponsored by:
CloudForgeLabs  
https://cloudforgelabs.ainextstudios.com/  
support@ainextstudios.com

Built by:
Freddy D. Alvarez  
https://www.linkedin.com/in/freddy-daniel-alvarez/

For job opportunities, contact:
it.freddy.alvarez@gmail.com

## License

Personal, educational, and non-commercial use is free. Commercial use requires paid permission.
See `LICENSE` and `COMMERCIAL_LICENSE.md`.

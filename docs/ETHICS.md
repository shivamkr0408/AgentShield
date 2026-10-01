# Ethics statement

AgentShield is **defensive** security research: it builds and evaluates a defense against
prompt injection in LLM agents. This document states how the work stays within responsible,
authorized bounds.

## Purpose

The system, the dataset, and the adaptive attacker exist to **measure and improve a defender**.
Nothing here is intended to attack, or is usable to attack, any third-party system.

## Sandbox only

- All attacks run against **mock tools** in a disposable in-memory sandbox (`agents/sandbox.py`).
  The inbox, website, files, outbox, and HTTP endpoint are simulations; no email is sent, no URL
  is fetched off-machine, and file access is confined to a temporary copy of the fixtures.
- All "secrets" are **obviously fake** (`sk-acme-FAKE-…`, `FAKE-IBAN-…`). They are exfiltration
  *targets* for the sandbox, never real credentials. The repository contains no real secrets,
  tokens, or personal data.
- The adaptive attacker (`eval/attacker/`) only probes the local defender. It never contacts an
  external service, and it mutates seed attacks from the dataset rather than generating novel
  capability.

## Dataset

- The attack samples are for training and testing detectors. The corpus is released with a
  responsible-use note (see the dataset card) under CC BY 4.0.
- Payloads are kept at the level already documented in the public literature and benchmarks; the
  multilingual contribution is coverage of **known** techniques in new languages, not new attacks.
- No real personal data is included. Benign samples are authored or drawn from openly licensed
  sources; see `data/sources.md` and `docs/DATASHEET.md`.

## Dual-use consideration

Any injection dataset or attacker harness is dual-use. We mitigate this by: (1) confining
execution to the sandbox; (2) using fake targets; (3) framing every artifact as a defense
evaluation; (4) not optimizing attacks against real deployed systems; and (5) releasing under a
license and note that ask downstream users to keep to defensive research.

## Responsible disclosure

The gaps this project finds (e.g., obfuscations that evade naive filters) concern the project's
own components and well-known public weaknesses. If future work tests AgentShield against a
third-party product, it will follow that vendor's responsible-disclosure process and will not be
done without authorization.

## Contact

Questions about responsible use should go to the repository maintainer via GitHub issues.

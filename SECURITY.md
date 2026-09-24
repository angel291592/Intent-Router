# Security Policy

English | [简体中文](SECURITY.zh-CN.md)

## Reporting a vulnerability

Please report security issues **privately**, through GitHub's private vulnerability reporting:

**Security** tab on this repository → **Report a vulnerability**
(direct link: <https://github.com/angel291592/Intent-Router/security/advisories/new>).

Do not open a public issue for a security problem. You will get an acknowledgement, and the report
stays private until a fix is available.

## What is in scope

Intent-Router is a prompt-only skill: a markdown file plus reference documents and a JSON Schema.
There is no runtime, no server, and no code that handles untrusted input on its own. The realistic
issue classes are:

- A prompt-injection path where the skill's instructions cause an agent to take a harmful action
  (for example, reading or exfiltrating something the user did not intend).
- Instructions that cause an agent to write outside the workspace, or to act on an irreversible
  boundary without asking. The skill's only write is its own spec file under `.intent/` — a saved
  spec quotes the original request and the record values it probed, so in non-code domains it can
  carry customer data; whether `.intent/` is committed or ignored is the project's own decision.
- A weakness in the evaluation runner (`evals/run.py`) when pointed at untrusted fixtures.

## What is not in scope

- The behaviour of a specific harness or model. Report those as regular bugs, or upstream.
- The fixtures under `evals/fixtures/` (both of them): deliberately small probe targets, not
  shipped applications.

## Supported versions

Only the latest released version is supported. Fixes land on `main`; there are no maintained
release branches yet.

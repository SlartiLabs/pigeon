# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.5.x   | Yes       |
| < 0.5   | No        |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email the maintainer at **slartilabs@protonmail.com** with:

- A description of the issue and its potential impact.
- Steps to reproduce (or a proof-of-concept, if you have one).
- Any suggested mitigations.

You will receive an acknowledgement within **3 business days** and a resolution
or status update within **14 days**. Once a fix is released, a coordinated
disclosure can be arranged at your preference.

## Scope note

Pointer resolution in pigeon is confined to the repository root, which is a
key hardening measure against path-traversal in handoff and retrieval calls.

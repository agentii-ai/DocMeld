# Security Policy

## Supported Versions

DocMeld follows [Semantic Versioning](https://semver.org/). Security fixes are applied to the latest
released minor version.

| Version | Supported |
|---------|-----------|
| 0.3.x   | ✅        |
| < 0.3   | ❌        |

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report them privately via one of:

- GitHub's [private vulnerability reporting](https://github.com/agentii-ai/DocMeld/security/advisories/new)
  (preferred), or
- email **hello@agentii.xyz** with the subject line `DocMeld security`.

Include as much detail as you can: affected version, a description of the issue, and a minimal
reproduction if possible.

We aim to acknowledge reports within **5 business days** and to provide a remediation timeline after
triage. We follow a **90-day coordinated disclosure** window: once a fix is ready, we will coordinate
with the reporter to release the advisory and patch together. We will credit reporters who wish to be
acknowledged.

## Scope Notes

DocMeld processes untrusted documents (PDF/DOCX/PPTX) and, in the optional gold stage, sends extracted
text to a third-party LLM API. When integrating DocMeld:

- Treat document content and any AI-generated metadata as untrusted input downstream.
- Keep API keys out of source control — use `.env.local` (gitignored) or environment variables.
- The `docling` and `soffice` backends invoke heavier third-party tooling; review their own security
  advisories when enabling them.

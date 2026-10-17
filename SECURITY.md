# Security Policy

Security reports help protect Velmora and the people who run it.

## Supported versions

Velmora is in alpha. Security fixes are targeted at the latest available version; older alpha builds may not receive fixes. Check the repository's releases and [`VERSION`](VERSION) for version information.

## Reporting a vulnerability

**Do not disclose exploitable vulnerabilities in public issues or discussions.**

Use GitHub's private vulnerability reporting feature from the repository's **Security** tab when available:

https://github.com/xydojhuk/velmora/security/advisories/new

Include the affected version, a clear description, reproduction steps using synthetic data, impact and any suggested mitigation. Do not submit passwords, session cookies, tokens, personal data or database dumps.

## Deployment security

Operators are responsible for securing their infrastructure:

- Use HTTPS and limit access to administrative endpoints.
- Keep dependencies, container images and the host updated.
- Protect local configuration, bootstrap secrets and backup files.
- Rotate credentials after suspected exposure.
- Test backup restoration on an isolated installation.
- Never expose development Compose configurations or local secrets as a production deployment.

See [README.md](README.md) for local setup and testing instructions.

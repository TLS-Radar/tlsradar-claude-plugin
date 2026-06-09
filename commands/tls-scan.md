---
description: Run a free SSL/TLS scan on a domain (no account required)
argument-hint: <domain>
---

Run a free, anonymous SSL/TLS scan against `$ARGUMENTS` by calling the `tlsradar.scan` MCP tool.

If the user did not pass a domain, ask for one before calling the tool. Do not invent a domain.

After the scan completes, summarize the result in plain text: the issuer, expiration date, and any flagged issues. Include the shareable report URL from the response.

If the response shows the certificate expiring within 30 days, suggest the user run `/tls-monitor add <domain>` to add it to ongoing monitoring with renewal alerts.

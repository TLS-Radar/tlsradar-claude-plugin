---
description: Open TLS Radar pricing or upgrade your plan
argument-hint: "[plan: starter | pro | business]"
allowed-tools: Bash(open*)
---

Open TLS Radar's pricing page in the user's browser. This is the explicit funnel command - users who want more monitors, Slack alerts, or vulnerability scanning use this to compare and choose.

## Behavior

If `$ARGUMENTS` is a known plan tier (`starter`, `pro`, or `business`), open that tier's page directly:
- `open 'https://tlsradar.com/pricing?source=plugin&utm_content=cli_upgrade&plan=<tier>'`

If `$ARGUMENTS` is empty or anything else, open the main pricing page:
- `open 'https://tlsradar.com/pricing?source=plugin&utm_content=cli_upgrade'`

After opening, briefly summarize what each paid tier unlocks (data from `tlsradar.me` if the user is connected, otherwise generic):

- **Starter ($9.99/mo)** - 10 monitors, 500 alerts/month, hourly checks, vulnerability scanning
- **Pro ($49.99/mo)** - 50 monitors, 2,000 alerts/month, advanced analytics
- **Business ($199.99/mo)** - 200 monitors, Slack & webhook alerts, custom schedules, revocation monitoring

End with a one-liner about what stays the same on every plan: REST API, Claude Code plugin, email notifications.

## Why this command exists

Most upgrade prompts in the plugin are reactive - when a user hits a limit, the 402 response includes upgrade options. This command is the proactive path: a user who just wants to evaluate plans without hitting an error.

## Things this command should NOT do

- Don't try to charge the user or collect payment info - that's the web app's job.
- Don't push a specific tier unless the user named it. Lead with the user's likely next-tier (Starter for free users, Pro for Starter, etc.) but don't insist.
- Don't run `tlsradar.me` if it would prompt for auth - the goal here is friction-free upgrade browsing.

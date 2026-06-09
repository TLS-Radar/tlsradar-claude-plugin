# Tool-routing evals

The tool-name guard ([`scripts/verify_tool_names.py`](../scripts/verify_tool_names.py))
proves every tool a command *names* exists. It can't prove the model picks the
**right** tool for a user's request - the failure that actually breaks the
plugin. These evals close that gap.

## Cases

[`cases.jsonl`](cases.jsonl) - one JSON object per line:

```json
{"prompt": "scan the ssl on example.com", "expect": ["scan"]}
```

`expect` is the set of acceptable tools (more than one when the request is
legitimately ambiguous, e.g. renew → `cert_create` or `cert_renew`).

## Running

```bash
# Static coverage - no network, runs in CI. Asserts every expected tool is
# real and is referenced by the skill router (so routing is even possible).
python3 evals/run_evals.py

# Real model-routing eval - sends each prompt to a model with the tool list
# and the skill as system prompt, and checks the tool it calls.
ANTHROPIC_API_KEY=... pip install anthropic && python3 evals/run_evals.py --llm
```

The static check runs on every PR via `.github/workflows/verify-contracts.yml`.
The `--llm` check is opt-in (it costs tokens); run it locally after changing the
skill or a tool description, or wire it into a gated job.

## Adding a case

Add a line to `cases.jsonl`. If the static check then fails with "not
referenced in SKILL.md," the skill router doesn't mention that tool - add a row
to the skill's "Choosing the right tool" table so the model can learn to pick
it. (That's the check doing its job: it caught a missing `monitor_remove` row
when these evals were first added.)

# Safety & Limitations

## What Preflight Does
- Reviews git diffs using Claude — flags potential bugs, security issues, style violations, and standards deviations
- Generates PR descriptions from diff content
- Indexes merged PR patterns from GitHub into a local vector store

## What Preflight Does NOT Do
- It does not block merges or enforce policy — it's advisory only
- It does not run or execute code
- It does not store diffs or code on any external server (only your Anthropic API key's usage logs)
- It does not access your codebase beyond the diff you provide

## Sensitive Data in Diffs
- If a diff contains secrets (API keys, passwords), those will be sent to the Anthropic API
- Preflight's security pass will flag hardcoded secrets as critical violations
- Do not use Preflight if your organization prohibits sending code to third-party AI APIs

## Model Limitations
- Claude may miss bugs that require deep runtime context or external knowledge
- False positives are possible — all comments are suggestions, not verdicts
- The standards agent is only as good as the patterns indexed from your repo history

## GitHub Indexer
- Requires a GitHub token with `repo` read scope
- Fetches PR metadata and file diffs — no code is modified
- Stores patterns locally in `.chroma/` — nothing is sent to external services beyond GitHub and Anthropic

## Known Limitations
- Diff context is limited to the changed lines — agents cannot see full file context
- Very large diffs (>8k tokens) may be truncated
- The standards agent needs at least a few merged PRs to build meaningful patterns
